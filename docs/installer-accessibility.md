# Calamares accessibility adapter

A guest-side read-only module discovers the desktop AT-SPI bus and enumerates
the application tree using gdbus, without extra Python packages or changes to
the shipped ISO. The observed registry from candidate run 45750583089
responded successfully after the address parsing fix. Calamares application
visibility and its individual widget names still require runtime evidence.

The inspector never invokes a widget action. It refuses an ambiguous
application root, limits traversal depth, nodes and time, and reports
missing/partial evidence. A separate VM input driver can use the observed
controls only after they are identified. No installation is certified by
this discovery module.
