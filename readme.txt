SNMP agent for working with custom MIB files, protocol version - 2c, transport - IPv4


Used Python packages:
- pysnmp 7.1.16
- pysmi 1.5.9
(install via PIP if not present)


# This website was used for MIB file validation:
https://www.simpleweb.org/ietf/mibs/validate/

# Exec this command in Linux terminal to compile MIB files into .py format (mibdump is utility of pysmi)
mibdump --generate-mib-texts --destination-format pysnmp ./<filename>.mib
# Compiled .py files will be placed to ~/.pysnmp/mibs

