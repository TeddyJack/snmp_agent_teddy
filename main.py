from snmp_agent import SnmpAgent
from time import sleep
from random import randint


my_agent = SnmpAgent('127.0.0.1', 1161, 'public', 'GRIFFIN')

(serialNumber, temperature, table, name, age, notification) = my_agent.import_symbols(
    "serialNumber", "temperature", "table", "name", "age", "notification")

# write some constant scalar value
my_agent.write_scalar(serialNumber, "0421")

# endlessly rewrite other scalar and tabular values with random numbers
names = ['Audrey', 'Suzie', 'Kristen', 'Rodrigo', 'Mickey']
while True:
    my_agent.write_scalar(temperature, randint(-100, 100))
    for i in range(5):
        my_agent.write_row(table, i + 1, [names[i], randint(0, 80)])
    my_agent.send_notif(notification, ['Nelly', randint(80, 100)])
    sleep(3)
