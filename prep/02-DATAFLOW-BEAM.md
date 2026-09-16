# Dataflow & Apache Beam

The JD names Dataflow explicitly. Even if your day job is BigQuery-centric, you must be
able to hold 10 minutes here without flinching.

---

## 1. The framing sentence

> "Beam is the programming model — one API that expresses batch and streaming as the
> same thing, where **batch is just streaming over a bounded PCollection**. Dataflow is
> Google's managed runner for it: serverless, autoscaling, and it takes over shuffle and
> state so I don't run a cluster. The value of the abstraction is that the windowing and
> late-data semantics I write are the same whether the source is a GCS file or a Pub/Sub
> subscription."

**"Batch is a special case of streaming"** is the sentence that shows you understand Beam
rather than having read the quickstart.

---

## 2. Core vocabulary — must be instant

| Term | One line |
|---|---|
| **Pipeline** | the whole DAG of transforms |
| **PCollection** | a distributed, immutable dataset; **bounded** or **unbounded** |
| **PTransform** | an operation: `ParDo`, `GroupByKey`, `Combine`, `Flatten`, `Partition` |
| **ParDo / DoFn** | per-element function — the `map`/`flatMap` primitive; `@setup`, `@start_bundle`, `@process`, `@finish_bundle`, `@teardown` |
| **GroupByKey / CoGroupByKey** | the shuffle; CoGBK = join of N keyed PCollections |
| **Combine** | associative+commutative aggregation — gets a **combiner lifted to the map side**, so prefer it over GBK+iterate |
| **Side input** | a small, broadcast-to-every-worker view of another PCollection (lookup/dimension table) |
| **Side output / tagged output** | multiple outputs from one DoFn — **this is how you build a dead-letter path** |
| **Windowing** | divides an unbounded PCollection by event time |
| **Watermark** | the runner's belief about event-time progress — "I think I've seen everything up to T" |
| **Trigger** | *when* a window emits a pane (early / on-time / late) |
| **Allowed lateness** | how long after the watermark passes the window end that late data is still accepted |
| **Accumulation mode** | `ACCUMULATING` (each pane restates the full result) vs `DISCARDING` (each pane is a delta) |
| **State & Timers** | per-key-per-window mutable state + event/processing-time callbacks — for custom sessionisation, dedup, alerting |

---

## 3. Windowing — draw it if you can

- **Fixed (tumbling)** — non-overlapping, e.g. every 5 min. "Revenue per 5 minutes."
- **Sliding (hopping)** — size + period; overlapping, an element is in multiple windows.
  "Trailing 1-hour count, updated every minute."
- **Session** — gap-based; closes after N minutes of inactivity **per key**. "User sessions."
- **Global** — the default; for unbounded data it's only useful with a non-default trigger.

**The pitfall answer:** *"With sliding windows, an element belongs to `size/period`
windows simultaneously, so a 24-hour window sliding every minute multiplies your state
and your output volume by 1,440. People design themselves into a cost problem that way."*

---

## 4. Watermarks, triggers, lateness — the question that sorts the field

**Q: "Data arrives late. What happens?"**

> It depends on where it lands relative to the watermark and allowed lateness. The
> watermark is a heuristic for event-time completeness — for Pub/Sub, Dataflow derives it
> from the oldest unacknowledged message's timestamp. When the watermark passes the end
> of a window, the **on-time pane** fires. If an element arrives after that but within
> **allowed lateness**, it triggers a **late pane**, and whether that pane is a
> restatement or a delta depends on the accumulation mode. If it arrives after allowed
> lateness expires, Beam **drops it** — which is why for anything financial I route
> dropped/malformed records to a dead-letter sink via a tagged output rather than
> letting them vanish. Silently dropping data is how you lose the business's trust.

**Trigger vocabulary:**
```python
Window.into(FixedWindows(60))
  .triggering(
     AfterWatermark(
        early=AfterProcessingTime(30),        # speculative results every 30s
        late=AfterCount(1)))                  # refire on each late element
  .with_allowed_lateness(Duration(hours=1))
  .accumulating_fired_panes()
```
**The trade-off to state:** early triggers buy latency at the cost of correctness and
downstream churn; long allowed lateness buys completeness at the cost of **state size**,
because the runner must keep every window open that long.

---

## 5. Batch vs streaming on Dataflow — service internals worth naming

- **Streaming Engine** — moves window state and shuffle off the worker VMs into the
  service backend. Smaller workers, much faster autoscaling, cheaper. **Default now;
  always enable it.**
- **Dataflow Shuffle** — the batch equivalent: service-side shuffle instead of on-VM.
- **Dataflow Prime** — vertical autoscaling + right-fitting per stage.
- **FlexRS** — batch at reduced cost using preemptible VMs with a scheduling delay (up to
  6h). Good for non-urgent backfills; say this if asked about cost.
- **Autoscaling** — batch scales on throughput/backlog; streaming on backlog **and** CPU.
  **Update** (in-place with state migration) vs **Drain** (stop ingesting, flush open
  windows, then stop) vs **Cancel** (immediate, loses in-flight). *"Drain for a clean
  deploy, Update for a compatible code change, Cancel only when I don't care about
  in-flight data."* — a genuinely operational answer.

---

## 6. Templates — the ops question

| Type | What it is |
|---|---|
| **Classic template** | pipeline graph staged to GCS at build time; `ValueProvider` for runtime params; graph is fixed |
| **Flex template** | pipeline packaged as a **Docker image**; graph built at launch, so branching on parameters works; the modern default |
| **Google-provided templates** | ~40 off-the-shelf (Pub/Sub→BigQuery, GCS Text→BigQuery, JDBC→BigQuery, Datastream→BigQuery) |

**Say this:** *"For a straight Pub/Sub-to-BigQuery landing job I'd use the Google-provided
template with a UDF and a dead-letter table before writing custom Beam — no code to
maintain and it already handles the failure path. I'd only write custom Beam when the
transform has real logic in it."* That's a senior, cost-aware answer and interviewers
notice when a candidate *doesn't* reach for code first.

---

## 7. Dataflow vs the alternatives — asked in every services-firm interview

| Choose | When |
|---|---|
| **Dataflow** | streaming with event-time semantics, or a batch transform too complex for SQL; unified batch+stream code; no cluster to manage |
| **Dataproc** | existing Spark/Hive/HBase estate, lift-and-shift migrations, Spark ML, team skill is Spark; ephemeral clusters per job |
| **BigQuery (ELT)** | the transform is expressible in SQL and the data is already landed — **usually cheaper and simpler; default here** |
| **Data Fusion** | visual/low-code CDAP pipelines for teams without deep coding; 100+ connectors; expensive (instance runs hourly) |
| **Cloud Functions / Run** | small event-driven glue, e.g. "a file landed in GCS → trigger a load job" |
| **Dataform** | SQL-first in-warehouse transformation, Google's dbt equivalent |

**The line that wins:**
> "My default is ELT into BigQuery, because compute I don't run is compute I don't tune.
> I reach for Dataflow when I need event-time windowing, per-key state, or enrichment
> that can't be a SQL join — and for Dataproc when there's an existing Spark estate,
> because rewriting working Spark into Beam is a migration cost with no business payoff."

---

## 8. A Python Beam pipeline you can write on a whiteboard

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions

class ParseEvent(beam.DoFn):
    def process(self, element):
        import json
        try:
            rec = json.loads(element.decode("utf-8"))
            yield beam.pvalue.TaggedOutput("valid", rec) if False else rec
        except Exception as e:                       # never let one bad record kill the job
            yield beam.pvalue.TaggedOutput("dead_letter",
                                           {"payload": element.decode("utf-8", "replace"),
                                            "error": str(e)})

opts = PipelineOptions(streaming=True)
with beam.Pipeline(options=opts) as p:
    parsed = (p
        | "Read"  >> beam.io.ReadFromPubSub(subscription=SUB).with_output_types(bytes)
        | "Parse" >> beam.ParDo(ParseEvent()).with_outputs("dead_letter", main="valid"))

    (parsed.valid
        | "Window" >> beam.WindowInto(beam.window.FixedWindows(60))
        | "Key"    >> beam.Map(lambda r: (r["product_id"], r["amount"]))
        | "Sum"    >> beam.CombinePerKey(sum)
        | "Shape"  >> beam.Map(lambda kv: {"product_id": kv[0], "revenue": kv[1]})
        | "ToBQ"   >> beam.io.WriteToBigQuery(
              TABLE,
              write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
              method=beam.io.WriteToBigQuery.Method.STORAGE_WRITE_API))

    (parsed.dead_letter | "DLQ" >> beam.io.WriteToBigQuery(DLQ_TABLE, ...))
```

**Points scored by this snippet:** tagged output dead-letter, explicit windowing,
`CombinePerKey` not `GroupByKey`, Storage Write API. Mention each as you write it.

---

## 9. Six Dataflow gotchas worth volunteering

1. **`GroupByKey` on an unbounded PCollection without windowing** fails — global window
   never closes. The runner tells you, but knowing why is the point.
2. **Hot keys** — one key dominates a `GroupByKey`. Fixes: `Combine` (map-side
   combining), `withFanout()` / `withHotKeyFanout()`, or salting the key.
3. **Small files in batch** — thousands of tiny GCS objects create thousands of splits
   and per-file overhead dominates. Compact upstream.
4. **`@setup` vs `@start_bundle`** — open expensive clients (BigQuery, Redis) in `@setup`,
   which runs once per worker, not per bundle. Opening a client per element is the classic
   performance bug in a DoFn.
5. **Side input size** — it's broadcast to every worker and held in memory. A "small
   lookup table" that grows to 5 GB will OOM the fleet. For large/changing lookups use
   `CoGroupByKey`, or a slowly-updating side input with periodic refresh.
6. **Fusion** — Dataflow fuses adjacent ParDos into one stage, which is usually good but
   can prevent parallelism after a low-cardinality step. Break fusion with a
   `Reshuffle` / `GroupByKey` when one element fans out to thousands.

---

## 10. Exactly-once, honestly

> "Pub/Sub delivery is **at-least-once**. Dataflow gives **exactly-once *processing***
> within the pipeline, through deterministic retries and checkpointed state. But
> end-to-end exactly-once is a property of the **sink**, not the runner — the sink has to
> be idempotent. Into BigQuery that means either the **Storage Write API with stream
> offsets**, which deduplicates on the server, or landing to a staging table and
> `MERGE`ing on a business key. If someone tells me they have exactly-once because
> they're using Dataflow, I'd want to know what the sink does on retry."

That answer, delivered calmly, is a strong-hire signal on its own.
