**Still under development and not functional!**

# DNS PTR updater
DNS PTR updater collects interface (IP address, IF-MIB::ifName)
details for a given list of devices, checks and updates PTR RR for those
IP addresses. Resulting PTR has a form of:

`hostname-ifname.domain.example`

DNS PTR updater features _Connectors_ for importing and exporting list fo
devices or existing PTR lists from/to 3rd party data sources.

It also features flexible JSON configuration file for simple implementation
of rules for:
- Ignoring devices or/and interfaces (regexp matching of hostname or ifName)
- Ignoring IP addresses (matching prefixes in CIDR notation)
- Default and per host community strings (regexp matching of hostname)
- List of name servers to query
- List of name servers to update
- List of domain names to build FQDN from
- Connector configuration

## Device PTR check
`device_ptr_check` is a Python script that displays info about specific device.
It shows a list of interfaces that have IP addresses configured, existing
PTR, IP address and a current status of PTR.
~~~~
╒═══════════════════════════════════════════════════════════════════════════════════════════════╕
│ Device:       r-sc-3.domain.example                                                           │
│ Interfaces:   10                                                                              │
│ IP addresses: 10                                                                              │
╞═══════════════════════════════════════════════════════════════════════════════════════════════╡
│ifName                     PTR                                          IP address             │
╞═══════════════════════════════════════════════════════════════════════════════════════════════╡
│MgmtEth0/RSP0/CPU0/0     ┌ r-sc-3.oobm.domain.example                   192.0.2.210            │
│                         └─► r-sc-3-mg0-0-0-0..domain.example                                  │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│BVI439                   ┌ r-sc-2-vl410.domain.example                  192.0.2.177            │
│                         └─► r-sc-3-bvi439.domain.example                                      │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│BVI63                    i r-sc-3-bvi63.domain.example                  172.28.0.1             │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│BVI64                    ┌ dynamic-192-0-2-1.domain.example             192.0.2.1              │
│                         └─► r-sc-3-bvi64.domain.example                                       │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│BVI65                    i r-sc-3-bvi65.domain.example                  10.137.148.1           │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│Loopback0                ◆ r-sc-3.domain.example                        192.0.2.249            │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│BVI67                    i r-sc-3-bvi67.domain.example                  172.28.16.1            │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│BVI68                    ■ r-sc-3-bvi68.domain.example                  192.0.2.193            │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│BVI69                    i r-sc-3-bvi69..domain.example                 10.137.47.1            │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│Bundle-Ether1.230        ┌ r-sc-4-gi0-0-230.domain.example              192.0.2.121            │
│                         └─► r-sc-3-bu1-230.domain.example                                     │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
╘═══════════════════════════════════════════════════════════════════════════════════════════════╛
~~~~

## Batch DNS PTR update
`dns-update.py` is a Python script that loads devices and PTRs from external sources
(via Connectors). It merges the list of PTRs loaded through Connector with
the PTR list it obtained from each device.
~~~~
Loaded connectors: ObserviumConnector
Loaded 10 device(s) from 1 connector(s)
│▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌▌│ 100%
╒═════════════════════════════════════╤══════╤════════╤════════╤══════════╤══════════╤══════════╕
│Device                               │ OK   │ UPDATE │ CREATE │ NO AUTH  │ IGNORED  │ UNKNOWN  │
╞═════════════════════════════════════╪══════╪════════╪════════╪══════════╪══════════╪══════════╡
│dhcp.domain.example                  │ 1    │ 0      │ 0      │ 0        │ 1        │ 0        │
│imap.different-domain.example        │ 0    │ 2      │ 1      │ 0        │ 1        │ 0        │
│mtik-pb-2.domain.example             │ 1    │ 2      │ 0      │ 0        │ 0        │ 0        │
│edge-nv-1.domain.example             │ 5    │ 0      │ 0      │ 1        │ 1        │ 0        │
│cns2.domain.example                  │ 1    │ 1      │ 0      │ 0        │ 1        │ 0        │
│olt-sc-1.domain.example              │ 2    │ 0      │ 0      │ 0        │ 0        │ 0        │
│r-kp-1.domain.example                │ 11   │ 1      │ 1      │ 0        │ 0        │ 0        │
│asa-bg-1.domain.example              │ 2    │ 0      │ 0      │ 0        │ 0        │ 0        │
│avas.domain.example                  │ 1    │ 0      │ 0      │ 0        │ 1        │ 0        │
│asa-bo-2.domain.example              │ 2    │ 0      │ 0      │ 0        │ 0        │ 0        │
╘═════════════════════════════════════╧══════╧════════╧════════╧══════════╧══════════╧══════════╛
~~~~