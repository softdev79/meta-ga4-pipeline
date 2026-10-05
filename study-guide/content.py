"""Study-guide content, assembled from the part modules in reading order."""

import importlib

TITLE = "From Control-M Admin to Data Engineer"
SUBTITLE = ("An extensive study guide with code snippets and embedded flashcards, for a "
            "professional with 5 years in Control-M administration and software development")
AUTHOR = "Data Engineering Career Study Guide"
COVER_BLURB = ("SQL · Python · Data Modelling · Warehouses · Pipelines "
               "· Airflow · dbt · Spark · Kafka · Cloud · Data "
               "Quality · DevOps · Portfolio Projects · Interview Prep<br/><br/>"
               "Includes a Control-M → Airflow concept bridge, a 16-week roadmap and "
               "spaced-repetition flashcards throughout.")

PARTS = [
    "part1_foundations",
    "part2_sql_python",
    "part3_modeling_storage",
    "part4_pipelines_orchestration",
    "part5_spark_streaming_cloud",
    "part6_quality_devops",
    "part7_career",
]

BLOCKS = []
for name in PARTS:
    try:
        BLOCKS += importlib.import_module(name).BLOCKS
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
