# Changelog

This file should be used to track all changes to ToMaTo in a similar way to [VpnCloud](https://github.com/dswd/vpncloud.rs/blob/master/CHANGELOG.md)
Entries should be prefixed with some tags:
- Status tags: `added`, `fixed`, `changed`, `removed`
- Component tags: `backend_core`, `backend_users`, `web`, `cli`, `hostmanager`, `misc`
Entries should be sorted by component and status with important entries and entries with multiple components being on top.


### UNRELEASED (RUNNING ON SERVERS)
- [web, fixed] Fixed small menu display issue for vpncloud switches
- [backend, changed] Not using cache when building docker images so that most current packages get installed 
- [backend, changed] Using __slots__ for generic classes, attributes and schemas and tasks to save space and increase performance
- [backend, changed] Dumping more errors
- [backend, fixed] Fixed problem with dumping stack variables when dumping errors
- [backend, fixed] Fixed problem with non-existing error groups
- [backend, fixed] Fixed problem with accounting aggregation for topologies, users and organizations
- [backend, fixed] Gracefully handling errors on topology timeout
- [backend, fixed] Gracefully handling errors on host component synchronization
- [backend, fixed] Fixed profiling when server does not terminate
- [backend, fixed] Fixed problem when stopping external networks with inconsistent states
- [backend_core, fixed] Fixed problem when generating vpncloud networkids (BSON 8 byte ints)
- [backend_core, fixed] Fixed problem with changing permissions
- [backend_core, fixed] Fixed problem with dumpmanager collecting errors
- [backend, removed] Removed useless dump environment infos
- [web, fixed] Fixed small menu display issue for vpncloud switches
- [hostmanager, fixed] Fixed problem with vpncloud dropping ARP packets

### UNRELEASED (NOT RUNNING ON SERVERS)
- [backend_users, added] Created new user management service
- [backend_core, backend_users, web, added] New mandatory central config file and config parser.
- [backend_core, backend_users, web, changed] Complete rewrite of tomato-ctl.py
- [backend, backend_core, changed] Renamed backend to backend_core
- [backend_core, hostmanager, changed] Checking whether selected templates exist on hosts and selecting hosts accordingly
- [backend, web, changed] Changed docker mount points of tomato code
- [backend_core, changed] Backend_core no longer uses two separate ssl keys
- [web, fixed] Fixed problem with default executable archives
- [misc, fixed] Fixed data link in tutorial
### PLANNED UNTIL RELEASE
- [backend_core, backend_users, web] Old config files will not work anymore.
