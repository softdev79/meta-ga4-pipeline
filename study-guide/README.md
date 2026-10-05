# From Control-M Admin to Data Engineer: Study Guide

**[Data_Engineer_Study_Guide.pdf](Data_Engineer_Study_Guide.pdf)** is a 74-page study guide for
someone with about 5 years of Control-M administration and some software development who wants
to move into data engineering. It has 55 code snippets and 173 embedded flashcards.

## Contents

1. How to use this guide (Leitner spaced repetition)
2. Control-M to data engineering concept bridge
3. 16-week roadmap and certifications
4. Data engineering foundations
5. SQL (joins, window functions, MERGE, tuning, interview problems)
6. Python for data engineering
7. Data modelling (Kimball, SCD types)
8. Storage, file formats and warehouses
9. Pipeline patterns (idempotency, incremental loads, CDC, backfills)
10. Airflow (side-by-side Control-M JSON and Airflow DAG)
11. dbt
12. Spark
13. Streaming and Kafka
14. Cloud platforms
15. Data quality and governance
16. DevOps for data
17. Linux and shell
18. Portfolio projects (including a Control-M to Airflow converter)
19. Resume and interviews
20. Glossary and rapid-fire review deck

## Rebuilding the PDF

```bash
pip install reportlab pygments
python study-guide/build_pdf.py
```

The content lives in `part*.py` as plain data. `build_pdf.py` renders it.
