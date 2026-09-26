# SRE Postmortem RAG Assistant — Live Endpoint Evaluation

**Endpoint**: `https://ai-sre-1-9ldq.onrender.com/ask`  
**Date**: 2026-09-26  
**Total Questions**: 18  
**All responses**: ✅ 200 OK  
**Session ID**: `eval-run-001`

---

## GitHub DNS Outage

### Q1 — Root Cause
**Question**: What root cause initiated GitHub's DNS outage?

**Answer**: The outage began when a Puppet manifest bug caused the authoritative nameserver to be restarted after an IP‑address change, while the caching nameserver was not restarted. This mismatch triggered DNS query timeouts and led to the subsequent failures [Source 1].

**Sources retrieved**: `github_dns_outage.md`, `github_database_health_check.md`, `aws_seoul_dns_config.md`, `cloudflare_router_config.md`

---

### Q2 — Incident Response Worsening
**Question**: How did the incident response actions make the GitHub DNS outage worse?

**Answer**: During the response, engineers triggered a deployment that rebuilt the DNS zone file by calling an internal provisioning API—an API that itself relied on DNS. Because DNS was already failing, the rebuild produced a corrupt zone file that returned NXDOMAIN for many records. The corrupted file caused many processes on the file-servers to spawn and consume all available memory, further extending the outage's duration. In short, the redeployment meant to fix the problem actually introduced a bad zone file and memory exhaustion, worsening the incident [Source 1].

**Sources retrieved**: `github_dns_outage.md`, `github_database_health_check.md`, `aws_seoul_dns_config.md`, `cloudflare_tiered_cache.md`

---

### Q3 — Downtime Duration
**Question**: What was the total downtime duration reported for GitHub's DNS incident?

**Answer**: GitHub reported a total downtime of 1 hour and 35 minutes for the DNS incident [Source 1].

**Sources retrieved**: `github_dns_outage.md`, `github_database_health_check.md`, `aws_seoul_dns_config.md`, `cloudflare_tiered_cache.md`

---

## CircleCI Schema Deploy Incident

### Q4 — Triggering Change
**Question**: What deployment change triggered the CircleCI job-distribution outage?

**Answer**: The outage was triggered when a deployment altered the type of a PostgreSQL field used by CircleCI's job‑distribution service. The new deployment wrote new rows with the new field type, while existing rows still had the old type, causing strict schema validation to fail on every distributor scan and halting job distribution [Source 1].

**Sources retrieved**: `circleci_schema_deploy.md`, `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`, `github_database_health_check.md`

---

### Q5 — Every Scan Failure
**Question**: Why did CircleCI's job-distribution service fail on every distributor scan?

**Answer**: The deployment altered the data type of a PostgreSQL column that the job‑distribution service reads. After the change, newly written rows used the new column type while existing rows still had the old type. When the service scanned the table, its strict schema validation encountered rows with mismatched types, causing the validation to fail on every scan and halting distribution of work [Source 1].

**Sources retrieved**: `circleci_schema_deploy.md`, `github_database_health_check.md`, `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`

---

### Q6 — Rollback Insufficient
**Question**: Why was a simple rollback insufficient to fix the CircleCI deployment incident?

**Answer**: A simple rollback could not restore service because the deployment had already written data using the new column type. When the change was undone, those rows—created between the two deployments—became unreadable by the original schema. Consequently, the service could not resume normal operation simply by rolling back; it required a hand‑deployed build that ignored the problematic field and manual scaling to recover the data inconsistency [Source 1].

**Sources retrieved**: `circleci_schema_deploy.md`, `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`, `github_database_health_check.md`

---

## AWS Seoul DNS Config Incident

### Q7 — Configuration Mistake
**Question**: What configuration mistake caused the AWS Seoul region EC2 DNS outage?

**Answer**: The outage was caused by a configuration change that removed the setting that defines the minimum healthy‑host count for the EC2 DNS resolver fleet in the Seoul region. Without this setting, the fleet fell back to a very low default, causing the healthy‑host count to drop and resulting in failed in‑VPC DNS queries for about 84 minutes [Source 1].

**Sources retrieved**: `aws_seoul_dns_config.md`, `github_dns_outage.md`, `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`

---

### Q8 — Failure Duration
**Question**: How long did in-VPC DNS failures persist during the AWS Seoul EC2 incident?

**Answer**: The in‑VPC DNS queries failed for about 84 minutes during the AWS Seoul EC2 DNS resolver incident [Source 1].

**Sources retrieved**: `aws_seoul_dns_config.md`, `github_dns_outage.md`, `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`

---

### Q9 — AWS Remediations
**Question**: What remediations did AWS implement after the Seoul DNS resolver incident?

**Answer**: AWS responded by adding two safeguards: a semantic configuration‑validation step to catch erroneous changes, and an hourly throttling limit on how many DNS‑resolver hosts could be removed at once [Source 1].

**Sources retrieved**: `aws_seoul_dns_config.md`, `github_dns_outage.md`, `cloudflare_tiered_cache.md`, `cloudflare_router_config.md`

---

## Cloudflare Edge Router Outage

### Q10 — Router Crash Cause
**Question**: What caused all Cloudflare edge routers to crash during their router configuration incident?

**Answer**: A malformed router‑rule configuration was applied, and the bad router‑rule caused every Cloudflare edge router to crash, taking down the service [Source 1].

**Sources retrieved**: `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`, `aws_seoul_dns_config.md`, `github_dns_outage.md`

---

### Q11 — Classification
**Question**: How is the Cloudflare edge-router crash classified in postmortem records?

**Answer**: The Cloudflare edge‑router crash is classified as a configuration error in the post‑mortem record [Source 1].

**Sources retrieved**: `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`, `aws_seoul_dns_config.md`, `github_database_health_check.md`

---

## Cloudflare Tiered Cache Incident

### Q12 — HTTP Error Code
**Question**: What HTTP error code was returned to users during the Cloudflare Tiered Cache incident?

**Answer**: The incident caused some requests to return HTTP status 530 [Source 1].

**Sources retrieved**: `cloudflare_tiered_cache.md`, `cloudflare_router_config.md`, `github_database_health_check.md`, `aws_seoul_dns_config.md`

---

### Q13 — Duration and Peak Error Rate
**Question**: What was the total impact duration and peak error rate during Cloudflare's Tiered Cache incident?

**Answer**: The Tiered Cache incident impacted the service for nearly six hours, and at its worst about 5% of requests were failing (the peak error rate) [Source 1].

**Sources retrieved**: `cloudflare_tiered_cache.md`, `cloudflare_router_config.md`, `aws_seoul_dns_config.md`, `github_database_health_check.md`

---

### Q14 — Testing Blind Spot
**Question**: Why did Cloudflare's testing fail to catch the Tiered Cache bug before production?

**Answer**: Cloudflare's post‑mortem says the bug was missed because the test environment did not exercise the relevant code path. The change triggered a blind spot in the test suite – the problem was not observed when the change was released to the test environment – and the overall system complexity made it hard to catch it before production. [Source 1]

**Sources retrieved**: `cloudflare_tiered_cache.md`, `cloudflare_router_config.md`, `github_database_health_check.md`, `github_dns_outage.md`

---

## GitHub Database Health Check Incident (August 2024)

### Q15 — Cause of Read Failures
**Question**: What caused GitHub.com's read operations to fail in August 2024?

**Answer**: GitHub.com's read operations failed because a configuration change that was deployed to the GitHub.com databases altered how the routing‑service health‑check pings were answered. The change caused the production read‑only endpoint to be marked unhealthy and become inaccessible, blocking all read traffic for about 36 minutes until the change was reverted. [Source 1]

**Sources retrieved**: `github_database_health_check.md`, `github_dns_outage.md`, `cloudflare_tiered_cache.md`, `circleci_schema_deploy.md`

---

### Q16 — Downtime Duration
**Question**: How long was GitHub.com unavailable for read operations during the August 2024 database incident?

**Answer**: GitHub.com's read operations were unavailable for 36 minutes during the August 2024 database incident [Source 1].

**Sources retrieved**: `github_database_health_check.md`, `cloudflare_tiered_cache.md`, `github_dns_outage.md`, `circleci_schema_deploy.md`

---

### Q17 — GitHub Remediations
**Question**: What remediations did GitHub adopt after the August 2024 database routing health check incident?

**Answer**: The only remediation mentioned in the post‑mortem is that GitHub reverted the configuration change that had altered the routing‑service health‑check behaviour, restoring the production read‑only endpoint to a healthy state and ending the 36‑minute outage. [Source 1]

**Sources retrieved**: `github_database_health_check.md`, `cloudflare_tiered_cache.md`, `circleci_schema_deploy.md`, `cloudflare_router_config.md`

---

## Cross-Corpus Synthesis

### Q18 — Common Themes
**Question**: What are common themes in configuration incidents across AWS and Cloudflare?

**Answer**: The incidents from both AWS and Cloudflare share several recurring themes:

1. **A single configuration change triggered a large‑scale outage** – In each case the root cause was a config update that altered normal service behaviour (the Cloudflare edge‑router rule, the Cloudflare Tiered‑Cache setting, the GitHub database routing health‑check, and the AWS Seoul EC2 DNS resolver minimum‑healthy‑host setting) [Source 1][Source 2][Source 3][Source 4].

2. **Insufficient validation or testing of the change** – Cloudflare's Tiered‑Cache incident notes a "blind spot in tests" and that the problem was not observed in the test environment. AWS's post‑mortem lists "semantic configuration validation" as a remediation, implying that validation was missing when the change was applied [Source 2][Source 4].

3. **Complexity or hidden dependencies that made the impact hard to predict** – The Cloudflare edge‑router outage resulted from a "bad router‑rule configuration" that affected every edge router, while the Tiered‑Cache change caused unexpected HTTP 530 errors because of system complexity [Source 1][Source 2][Source 3].

4. **Remediation involved rolling back or restoring the original configuration, followed by added safeguards** – GitHub reverted the config change, AWS restored capacity and added validation and throttling of host removal, and the Cloudflare summaries imply that fixing the router rule restored service [Source 3][Source 4].

These themes illustrate that configuration‑driven incidents often stem from inadequate testing or validation of changes, the hidden complexity of the systems they affect, and the need for stricter safeguards and quick rollback mechanisms.

**Sources retrieved**: `cloudflare_router_config.md`, `cloudflare_tiered_cache.md`, `github_database_health_check.md`, `aws_seoul_dns_config.md`

---

*Generated automatically by querying the live production endpoint. All 18 responses returned HTTP 200.*
