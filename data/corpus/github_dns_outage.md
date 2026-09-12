# GitHub DNS outage

Source report: https://github.blog/news-insights/the-library/dns-outage-post-mortem/

This corpus record is a fixed summary from the public danluu/post-mortems index.

A Puppet manifest bug restarted the authoritative nameserver, but not the caching
nameserver, after an IP-address change. This caused DNS query timeouts. During incident
response, a deploy rebuilt the zone file from an internal provisioning API call that also
depended on DNS. That created a corrupt zone file that returned NXDOMAIN for many records.
Processes spawned on the file servers exhausted memory and extended the impact. GitHub
reported 1 hour and 35 minutes of partial downtime.
