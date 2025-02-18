from snmp_agent import SnmpAgent
from time import sleep
from random import randint
from threading import Thread


my_agent = SnmpAgent(1161, '127.0.0.1', 162, 'public', 'GRIFFIN')   # local manager
#my_agent = SnmpAgent(1161, '192.168.111.185', 162, 'public', 'GRIFFIN') # remote manager


def run_dispatcher():
    my_agent.run_dispatcher()
    

def update_vals_and_send_ntf():
    (serialNumber, temperature, table, notification) = my_agent.import_symbols(
        "serialNumber", "temperature", "table", "notification")
    my_agent.write_scalar(serialNumber, "0421")
    names = ['Audrey', 'Suzie', 'Kristen', 'Rodrigo', 'Mickey']
    while True:
        my_agent.write_scalar(temperature, randint(-100, 100))
        for i in range(5):
            my_agent.write_row(table, i + 1, [names[i], randint(0, 80)])
        my_agent.send_notif(notification, ['Nelly', randint(80, 100)])
        sleep(3)


th_dispatcher = Thread(target=run_dispatcher, daemon=True)
th_updater = Thread(target=update_vals_and_send_ntf, daemon=True)
th_dispatcher.start()
th_updater.start()


print('Main thread is running')
while True:
    sleep(3)