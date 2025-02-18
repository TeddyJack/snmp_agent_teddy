SNMP agent for working with custom MIB files, protocol version - 2c, transport - IPv4

########
# Info #
########

Used Python packages:
- pysnmp 7.1.16
- pysmi 1.5.9

This website was used for MIB file validation:
https://www.simpleweb.org/ietf/mibs/validate/




##############
# How to use #
##############

1) pip install pysnmp (if not installed)

2) pip install pysmi (if not installed)

3) Compile .MIB file into pysnmp format.
$ mibdump --generate-mib-texts --destination-format pysnmp ./GRIFFIN.mib

(mibdump utility comes with pysmi package)
Compiled .py file will be placed into ~/.pysnmp/mibs

WHEN USING YOUR .MIB FILES:
- Replace GRIFFIN.mib with your filename when compiling
- My main.py won't be working with you file obviously, but you can use it as example
- Each table in .MIB file must have it's own "rowStatus" column (always the last one)
(unique name for each table)

4) Run main.py
Every 3 seconds values (except serialNumber) are updated.
Also notification are sent.

5) Use MIB-browser or some NMS (network managing station) software with loaded GRIFFIN.MIB
to see results
Agent's port is 1161 not 161.
