# GitHub database routing health-check incident

Source report: https://github.blog/news-insights/company-news/github-availability-report-august-2024/

This corpus record is a fixed summary from the public danluu/post-mortems index.

A configuration change deployed to GitHub.com databases changed how hosts answered
routing-service health-check pings. The production read-only endpoint was marked
unhealthy and became inaccessible. With reads unavailable, the site was down for read
operations for 36 minutes, until the configuration change was reverted.
