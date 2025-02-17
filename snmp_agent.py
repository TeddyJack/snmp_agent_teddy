from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.smi import builder
from threading import Thread
import asyncio
from pysnmp.hlapi.v1arch.asyncio import *
import os


class SnmpAgent():

    def __init__(self, mngr_ip_addr, agent_port, community_string, mib_file_name):
        # Basic IPv4 and SNMPv2c setup
        snmpEngine = engine.SnmpEngine()
        config.add_transport(snmpEngine, udp.DOMAIN_NAME, udp.UdpTransport().open_server_mode((mngr_ip_addr, agent_port)))
        config.add_v1_system(snmpEngine, "my-area", community_string)
        config.add_vacm_user(snmpEngine, 2, "my-area", "noAuthNoPriv", (1, 3, 6), (1, 3, 6))
        snmpContext = context.SnmpContext(snmpEngine)
        mibInstrum = snmpContext.get_mib_instrum()
        mibBuilder = mibInstrum.get_mib_builder()

        # Load structure from MIB-file (<mib_file_name>.py) to context
        mibBuilder.add_mib_sources(builder.DirMibSource(os.path.expanduser("~") + '/.pysnmp/mibs'))
        mibBuilder.load_module(mib_file_name)


        # Create instances of all scalar objects in context
        (MibScalar, MibScalarInstance, MibTable, MibTableColumn) = mibBuilder.import_symbols(
            "SNMPv2-SMI", "MibScalar", "MibScalarInstance", "MibTable", "MibTableColumn")
        scalars = []
        tables = []
        for obj in mibBuilder.mibSymbols[mib_file_name].values():
            if obj.__class__ is MibScalar:
                scalars.append(obj)
            elif obj.__class__ is MibTable:
                tables.append(obj)
        for s in scalars:
            mibBuilder.export_symbols(mib_file_name, MibScalarInstance(s.name, (0,), s.syntax))
        
        # Count columns in tables
        for t in tables:
            n_columns = 0
            for obj in mibBuilder.mibSymbols[mib_file_name].values():
                if obj.__class__ is MibTableColumn and obj.name[:-2] == t.name:
                    n_columns += 1
                t.n_columns = n_columns
        
        # Register SNMP Applications at the SNMP engine for particular SNMP context
        cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.SetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
        cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)

        # Register an imaginary never-ending job to keep I/O dispatcher running forever
        snmpEngine.transport_dispatcher.job_started(1)

        # Create links to inner objects for other methods to access them
        self.snmpEngine = snmpEngine
        self.mibBuilder = mibBuilder
        self.mib_file_name = mib_file_name
        self.mibInstrum = mibInstrum
        self.community_string = community_string

        # Run dispatcher in new thread
        Thread(target=self.__dispatcher).start()


    def __dispatcher(self):
        # Run I/O dispatcher which would receive queries and send responses
        try:
            self.snmpEngine.open_dispatcher()
        except:
            self.snmpEngine.close_dispatcher()
            raise


    def stop(self):
        self.snmpEngine.close_dispatcher()


    def import_symbols(self, *sym_names):
        return self.mibBuilder.import_symbols(self.mib_file_name, *sym_names)


    def write_scalar(self, object_name, value):
        self.mibInstrum.write_variables((object_name.name + (0,), value))


    def write_row(self, table_name, row_idx, values, columns_names=None):
        arg = []
        if columns_names is None:
            column_idx = 2  # because 1 is rowIndex (inaccessible)
            for item in values:
                arg.append((table_name.name + (1, column_idx, row_idx), item))
                column_idx += 1
        else:
            arg = [(column_name.name, value) for column_name, value in zip(columns_names, values)]
        try:
            self.mibInstrum.write_variables(*arg, (table_name.name + (1, table_name.n_columns, row_idx), 'active'))
        except:
            self.mibInstrum.write_variables(*arg, (table_name.name + (1, table_name.n_columns, row_idx), 'createAndGo'))


    def delete_row(self, table_name, row_idx):
        # deleting inexisting row leads to error
        self.mibInstrum.write_variables((table_name.name + (1, table_name.n_columns, row_idx), 'destroy'))
    

    async def __send_notif_async(self, notif_name, values, obj_names=None):
        snmpDispatcher = SnmpDispatcher()

        if obj_names is None:
            arg = [(self.import_symbols(obj_item[1])[0].name, value) for obj_item, value in zip(notif_name.objects, values)]
        else:
            arg = [(obj_name.name, value) for obj_name, value in zip(obj_names, values)]

        result = await send_notification(
            snmpDispatcher,
            CommunityData(self.community_string, mpModel=1),
            await UdpTransportTarget.create(("127.0.0.1", 162)),
            "trap",
            NotificationType(ObjectIdentity(notif_name.name)).load_mibs().add_varbinds(*arg)
        )

        errorIndication, errorStatus, errorIndex, varBinds = result

        if errorIndication:
            print(errorIndication)

        snmpDispatcher.transport_dispatcher.close_dispatcher()
    

    def send_notif(self, notif_name, obj_names, values=None):
        asyncio.run(self.__send_notif_async(notif_name, obj_names, values))