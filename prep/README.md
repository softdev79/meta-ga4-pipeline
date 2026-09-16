# Round 2 prep — HCLTech Platform Engineer III (Data Engineer, GCP)

Built for the second technical round. Round 1's material is `../CHEATSHEET.md`
(Spark/Hadoop/migration); this pack is the **GCP-native** round the JD describes.

| File | What it's for |
|---|---|
| `00-BATTLE-PLAN.md` | How HCL's L2 actually runs, the scoring rubric, your opening 90 seconds, questions to ask |
| `01-BIGQUERY.md` | Architecture, partitioning/clustering, cost, MERGE/SCD, nested data, perf debugging, security |
| `02-DATAFLOW-BEAM.md` | Beam model, windowing/watermarks/triggers, templates, service internals, gotchas |
| `03-PUBSUB-STREAMING.md` | Pub/Sub semantics, streaming architecture, CDC, Kafka comparison, debug scenarios |
| `04-COMPOSER-AIRFLOW.md` | Logical dates, idempotency, the DAG factory, operators, debug scenarios, alerting |
| `05-PYTHON.md` | Language questions, coding problems, pandas, testing and engineering practice |
| `06-SQL.md` | Window functions, the classic puzzles, the traps, BigQuery-specific SQL, optimisation |
| `07-MODELING-WAREHOUSE.md` | Layered architecture, Kimball/Vault, facts & dims, ETL vs ELT, design principles |
| `08-DQ-GOVERNANCE.md` | Six dimensions, four gates, concrete checks, Dataplex, data contracts |
| `09-DBT.md` | Materialisations, incremental strategies, tests, snapshots, Slim CI, Talend/Data Fusion |
| `10-IAM-OPS-CICD.md` | IAM model, monitoring metrics that matter, Terraform, CI/CD, Agile, AI/ML |
| `11-SYSTEM-DESIGN.md` | Six scenarios with full model answers, and the method to use on any of them |
| `12-PROJECT-STORY.md` | **Your 3-minute pitch and every follow-up** — the highest-value file here |
| `13-BEHAVIORAL.md` | STAR stories, the eight to prepare, model answers, communication mechanics |
| `14-RAPID-FIRE.md` | 150 one-line Q&A for recall drilling |
| `15-MOCK-INTERVIEW.md` | Full 60-minute mock with the interviewer's scoring notes |
| `16-ROUND2-CHEATSHEET.md` | **The one-pager. Read this last.** |

## If you only have an hour
`16` → `12` (rehearse the pitch **out loud, twice**) → `14` → `13` §3.

## The single most important thing
Reported HCL rounds are *"discussion on projects and services used, and why particular
services were chosen over alternatives."* Every service on your CV is a question waiting to
happen, and the answer that scores is **define → contrast with the rejected alternative →
your example with a number → when I wouldn't**.
