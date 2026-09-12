# CircleCI job-distribution schema deployment incident

Source report: https://discuss.circleci.com/t/incident-report-november-8-2021-jobs-stuck-in-a-not-running-state/41890

This corpus record is a fixed summary from the public danluu/post-mortems index.

A deployment changed the type of a PostgreSQL field used by CircleCI's job-distribution
service. New rows used the new type while old rows retained the old type. Strict schema
validation then failed on every distributor scan, and work stopped being distributed.
Rolling back made rows written between the deployments unreadable, so recovery required a
hand-deployed build that ignored the field and manual scaling.
