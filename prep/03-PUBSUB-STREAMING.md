# Pub/Sub and streaming design

---

## 1. The model

Publisher → **Topic** → **Subscription(s)** → Subscriber. Fan-out is per subscription:
**one message is delivered to every subscription on the topic**, and within a
subscription to exactly one subscriber (competing consumers). Getting this right is the
most common design mistake — "I need two consumers" means **two subscriptions**, not two
subscribers on one subscription.

- **Delivery:** at-least-once by default. **Exactly-once delivery** is now available per
  subscription (within a cloud region) — it guarantees no redelivery after successful ack.
- **Ordering:** off by default. Enable **message ordering** and publish with an
  **ordering key** → messages with the same key are delivered in order (and it pins them
  to one region). Cost: throughput per key is serialised, so a hot ordering key throttles you.
- **Retention:** topic retention (up to 31 days, optional) and subscription retention of
  **unacknowledged** messages (default 7 days). **Seek** lets you replay to a timestamp
  or a snapshot — this is your streaming backfill/replay story.
- **Ack deadline:** default 10s, max 600s; the client library extends it automatically
  while processing. Exceeding it → redelivery → duplicates.
- **Dead-letter topic:** after N delivery attempts, move the message aside. **Always
  configure one.** A poison message without a DLQ is an infinite redelivery loop that
  looks like a throughput problem.
- **Push vs pull:** pull (client controls rate, best for Dataflow), push to an HTTPS
  endpoint (Cloud Run/Functions; Pub/Sub controls rate, needs a 2xx), **StreamingPull**
  (gRPC, lowest latency, what the client libs use).
- **Pub/Sub Lite** — deprecated/legacy zonal cheaper variant; know the name, don't propose it.
- **BigQuery subscription** — writes straight from Pub/Sub into BigQuery **with no
  Dataflow job at all**. **GCS subscription** does the same to files. Mention this:
  *"If the transform is nothing more than 'land the JSON', a BigQuery subscription removes
  an entire service from the architecture."* Big senior-signal answer.

---

## 2. The canonical streaming architecture (be able to draw it in 30 seconds)

```
 App / IoT / CDC
        |  publish (ordering key = entity_id)
        v
   Pub/Sub topic  ---> subscription A ---> Dataflow (Beam) ---> BigQuery (Storage Write API)
        |                                        |
        |                                        +--> dead-letter table (tagged output)
        +---> subscription B ---> Cloud Run (real-time alerting)
        +---> dead-letter topic ---> DLQ subscription ---> GCS / BQ for triage
```

Plus: **Cloud Monitoring alert on `subscription/oldest_unacked_message_age`** — this is
*the* streaming SLO metric. Backlog size tells you volume; oldest-unacked tells you
whether you're falling behind. Name it and you sound like you've run a stream.

---

## 3. Streaming vs batch — the decision, framed like a consultant

> "I start from the business question, not the technology. The right question is 'what
> decision gets made faster if this data is 5 minutes old instead of 6 hours old, and is
> that worth roughly an order of magnitude more operational complexity?' Streaming means
> you own watermarks, late data, state size, replay and 24/7 on-call. For most marketing
> and finance reporting, hourly micro-batch is the honest answer. Streaming earns its
> keep for fraud, personalisation, operational alerting, inventory — anywhere a human or
> a system acts on the event within minutes."

Then: *"A pattern I like is micro-batch as a first step — Pub/Sub into GCS in 5-minute
windows, loaded by a scheduled BigQuery load job, which is free — and only upgrading to
true streaming when the latency requirement actually appears."*

---

## 4. Debug scenarios they will hand you

**"Consumers are keeping up but the backlog keeps growing."**
→ Check `num_undelivered_messages` vs `oldest_unacked_message_age`. If oldest-unacked is
pinned and growing, you likely have a **poison message** being redelivered, or an
ordering key serialising a hot partition. Check the DLQ, check `ack_deadline` expiry rate.

**"We're seeing duplicates in BigQuery."**
→ Expected: Pub/Sub is at-least-once. Where's the dedup? Options: exactly-once
subscription, Storage Write API offsets, Beam `Deduplicate` transform over a time window
using a message attribute as the idempotency key, or a MERGE on a business key at the
sink. Ask **what the business key is** — if there isn't one, that's the real finding.

**"Latency spiked at 9 a.m. every day."**
→ Autoscaling lag on a diurnal spike. Streaming Engine + a higher `min_num_workers`, or
pre-warm. Also check whether a batch job is competing for the same slot reservation.

**"A bad schema change broke the pipeline."**
→ **Pub/Sub schemas** (Avro/Protobuf attached to a topic) reject malformed publishes at
the edge. Downstream, a dead-letter path plus a permissive landing table (raw JSON string
+ ingest timestamp) means a schema change degrades rather than halts. This is the
**schema-on-read landing zone** argument — say it, it's the right answer.

---

## 5. CDC — comes up constantly, and it's a differentiator

- **Datastream** — Google's serverless CDC from Oracle/MySQL/PostgreSQL/SQL Server into
  BigQuery or GCS. The **Datastream-to-BigQuery** path now does the MERGE for you.
- **Debezium → Kafka → Pub/Sub** for on-prem/multi-cloud, or Kafka→BigQuery connectors.
- The hard parts you should name: **initial snapshot + ongoing stream without gaps or
  duplicates**, **schema drift** (DDL on the source), **deletes** (soft-delete flag vs
  hard delete), and **out-of-order events** — which is why CDC rows carry a log sequence
  number and you MERGE on `(pk)` taking `MAX(lsn)`, not the last row that arrived.

```sql
-- CDC apply: last-writer-wins by log sequence number, not arrival order
MERGE target T USING (
  SELECT * FROM staging
  QUALIFY ROW_NUMBER() OVER (PARTITION BY pk ORDER BY lsn DESC) = 1
) S
ON T.pk = S.pk
WHEN MATCHED AND S.op = 'D' THEN DELETE
WHEN MATCHED AND S.lsn > T.lsn THEN UPDATE SET ...
WHEN NOT MATCHED AND S.op != 'D' THEN INSERT ROW;
```

---

## 6. Kafka vs Pub/Sub (asked when the client has a Kafka estate)

| | Pub/Sub | Kafka |
|---|---|---|
| Ops | zero, serverless, global | you run brokers/ZK-KRaft (or pay Confluent) |
| Scaling | automatic | repartitioning is a manual, disruptive operation |
| Ordering | per ordering key, opt-in | per partition, inherent |
| Retention | 7–31 days | unbounded / compacted topics |
| Replay | seek to timestamp/snapshot | offset-based, cheap and precise |
| Ecosystem | GCP-native | Connect, Streams, ksqlDB, huge connector library |

> "If a client already runs Kafka I don't propose ripping it out; I bridge it — Kafka
> Connect to Pub/Sub or straight into BigQuery. Migration cost with no business payoff is
> the easiest architecture argument to lose."
