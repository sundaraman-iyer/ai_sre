# Cloudflare Tiered Cache incident

Source report: https://web.archive.org/web/20221112015610/https://blog.cloudflare.com/partial-cloudflare-outage-on-october-25-2022/

This corpus record is a fixed summary from the public danluu/post-mortems index.

A Tiered Cache change caused some requests to fail with HTTP status 530. The total impact
lasted nearly six hours, with roughly 5% of requests failing at peak. Cloudflare attributed
the missed detection to system complexity and a blind spot in tests: the problem was not
observed when the change was released to the test environment.
