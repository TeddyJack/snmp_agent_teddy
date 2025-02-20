from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.smi import builder
import asyncio
from pysnmp.hlapi.v1arch.asyncio import *
import os


class SnmpAgent():

    def __init__(self, agent_port, mngr_ip_addr, mngr_port, community_string, mib_file_name):
        # Basic IPv4 and SNMPv2c setup
        snmpEngine = engine.SnmpEngine()
        config.add_transport(snmpEngine, udp.DOMAIN_NAME, udp.UdpTransport().open_server_mode(('0.0.0.0', agent_port)))
        config.add_v1_system(snmpEngine, "my-area", community_string)
        config.add_vacm_user(snmpEngine, 2, "my-area", "noAuthNoPriv", (1, 3, 6), (1, 3, 6))
        snmpContext = context.SnmpContext(snmpEngine)
        mibInstrum = snmpContext.get_mib_instrum()
        mibBuilder = mibInstrum.get_mib_builder()

        # Load structure from MIB-file (<mib_file_name>.py) to context
        mibBuilder.add_mib_sources(builder.DirMibSource(os.path.expanduser("~") + '/.pysnmp/mibs'))
        mibBuilder.load_module(mib_file_name)

        # Find all tabular objects and count columns number
        (MibTable, MibTableColumn) = mibBuilder.import_symbols(
            "SNMPv2-SMI", "MibTable", "MibTableColumn")
        tables = []
        for obj in mibBuilder.mibSymbols[mib_file_name].values():
            if obj.__class__ is MibTable:
                tables.append(obj)
                obj.rows_indexes = []
        for t in tables:
            t.n_columns = 0
            for obj in mibBuilder.mibSymbols[mib_file_name].values():
                if obj.__class__ is MibTableColumn and obj.name[:-2] == t.name:
                    t.n_columns += 1
        
        # Register SNMP Applications at the SNMP engine for particular SNMP context
        cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.SetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
        cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)

        # Create links to attributes for other methods to access them
        self.snmpEngine = snmpEngine
        self.mibBuilder = mibBuilder
        self.mib_file_name = mib_file_name
        self.mibInstrum = mibInstrum
        self.community_string = community_string
        self.mngr_ip_addr = mngr_ip_addr
        self.mngr_port = mngr_port


    def run_dispatcher(self):
        # Register an imaginary never-ending job to keep I/O dispatcher running forever
        self.snmpEngine.transport_dispatcher.job_started(1)
        # Run I/O dispatcher which would receive queries and send responses
        try:
            self.snmpEngine.open_dispatcher()
        except:
            self.snmpEngine.close_dispatcher()
            raise


    def stop_dispatcher(self):
        self.snmpEngine.close_dispatcher()


    def import_symbols(self, *sym_names):
        return self.mibBuilder.import_symbols(self.mib_file_name, *sym_names)


    def write_scalar(self, object_name, value):
        try:
            self.mibInstrum.write_variables((object_name.name + (0,), value))
        except:
            (MibScalarInstance, ) = self.mibBuilder.import_symbols("SNMPv2-SMI", "MibScalarInstance")
            self.mibBuilder.export_symbols(self.mib_file_name, MibScalarInstance(object_name.name, (0,), object_name.syntax))
            self.mibInstrum.write_variables((object_name.name + (0,), value))


    def write_row(self, table_name, row_idx, values):
        # column idx starts from 2 because 1 is rowIndex
        args = [(table_name.name + (1, i + 2, row_idx), value) for i, value in enumerate(values)]
        try:
            self.mibInstrum.write_variables(*args, (table_name.name + (1, table_name.n_columns, row_idx), 'active'))
        except:
            self.mibInstrum.write_variables(*args, (table_name.name + (1, table_name.n_columns, row_idx), 'createAndGo'))
            table_name.rows_indexes.append(row_idx)
    

    def write_cells(self, table_name, row_idx, columns_names, values):
        # possible only if row exists
        if row_idx not in table_name.rows_indexes:
            return False
        args = [(column_name.name + (row_idx,), value) for column_name, value in zip(columns_names, values)]
        self.mibInstrum.write_variables(*args, (table_name.name + (1, table_name.n_columns, row_idx), 'active'))
        return True


    def delete_row(self, table_name, row_idx):
        if row_idx not in table_name.rows_indexes:
            return False
        self.mibInstrum.write_variables((table_name.name + (1, table_name.n_columns, row_idx), 'destroy'))
        table_name.rows_indexes.remove(row_idx)
        return True
    

    def clear_table(self, table_name):
        if not table_name.rows_indexes:
            return False
        args = [(table_name.name + (1, table_name.n_columns, row_idx), 'destroy') for row_idx in table_name.rows_indexes]
        self.mibInstrum.write_variables(*args)
        table_name.rows_indexes.clear()
        return True
    

    async def __send_notif_async(self, notif_name, values, obj_names=None):
        snmpDispatcher = SnmpDispatcher()

        if obj_names is None:
            arg = [(self.import_symbols(obj_item[1])[0].name, value) for obj_item, value in zip(notif_name.objects, values)]
        else:
            arg = [(obj_name.name, value) for obj_name, value in zip(obj_names, values)]

        result = await send_notification(
            snmpDispatcher,
            CommunityData(self.community_string, mpModel=1),
            await UdpTransportTarget.create((self.mngr_ip_addr, self.mngr_port)),
            "trap",
            NotificationType(ObjectIdentity(notif_name.name)).load_mibs().add_varbinds(*arg)
        )

        errorIndication, errorStatus, errorIndex, varBinds = result

        if errorIndication:
            print(errorIndication)

        snmpDispatcher.transport_dispatcher.close_dispatcher()
    

    def send_notif(self, notif_name, values, obj_names=None):
        asyncio.run(self.__send_notif_async(notif_name, values, obj_names))