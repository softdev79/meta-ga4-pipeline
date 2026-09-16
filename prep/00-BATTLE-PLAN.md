# Round 2 — HCLTech Platform Engineer III (Data Engineer, GCP)

**Location:** Gautam Buddha Nagar (Noida). **Level:** Platform Engineer III, 5+ yrs.
**Round:** L2 — typically the SME / technical panel round.

---

## 1. What round 2 actually is at an Indian services firm

From candidate reports across HCLTech/HCL interview boards, the shape is consistent:

| Round | Who | What it really tests |
|---|---|---|
| L1 | Recruiter / junior tech | Screening: does the CV match the JD, availability, notice period |
| **L2 (today)** | **SME / delivery lead** | **Project deep-dive + "why this service over that one" + medium SQL/Python + scenario debugging** |
| L3 | Project Manager / client-facing | Communication, client handling, coaching juniors, fitment |
| HR | HR | Comp, notice, location |

Reported difficulty is **easy-to-medium**, and reported content is **"discussion on projects and services used along with some medium-level SQL and Python coding."** Candidates repeatedly say they were asked about
*"services used in big data projects in detail, including scenarios explaining why particular services were chosen over alternatives."*

### The single most important implication

**This is not a DSA round. It is a "can you defend your architecture" round.**

You will not be asked to invert a binary tree. You will be asked:

> "You used Dataflow here. Why not Dataproc? Why not just load into BigQuery and do it in SQL?"

Every service on your CV is a question waiting to happen. For each one you must have:
**what it does → why you picked it → what you rejected → what it cost you.**

An answer without the rejected alternative scores a 2/5. An answer with the
rejected alternative *and a number attached* scores a 5/5.

---

## 2. How an SME silently scores you

This is the rubric in the interviewer's head, whether or not it's on paper:

| Score | What it sounds like |
|---|---|
| 1 | Recites a definition. "Dataflow is a serverless data processing service." |
| 2 | Definition + one correct detail. No trade-off. |
| 3 | Definition + contrast with the alternative. Generic example. |
| 4 | Contrast + a real example **from their own work**. |
| **5** | **Contrast + own example + a number + "here's when I would NOT do this."** |

**Your answer template — burn this in:**

> **Define** (one sentence) → **Contrast** with the alternative → **Your project**, with a number → **The trade-off / when I wouldn't**.

Twenty seconds each for the first three, ten for the last. ~60–75 seconds per answer.
Longer than that and you're rambling; shorter and you sound shallow.

### The three phrases that buy you credibility

- *"The trade-off there was…"*
- *"That bit us in production when…"*
- *"I'd push back on that if…"* (used carefully — shows seniority, not arrogance)

### The three phrases that cost you credibility

- *"Basically…"* (filler, every sentence)
- *"I think it's something like…"* → say **"I'd check the docs, but my working model is X"** instead
- Bluffing. An SME can smell a fabricated number at 20 paces. **"I haven't used Data Fusion in production — I know it's the visual CDAP-based tool, and here's where I'd reach for it"** is a *strong* answer. Pretending is a disqualifier.

---

## 3. Your asymmetric advantage

You have a real, defensible GCP pipeline in this repo — Meta Ads → GA4 → BigQuery,
Airflow-orchestrated, with genuinely hard problems solved (grain, identity,
restatement, attribution, rate limiting). **Most candidates at this level cannot
describe one honest engineering trade-off.** You can describe six.

**Drive every abstract question back to this project.** See `12-PROJECT-STORY.md`.
The interviewer's notes at the end will say *"has actually built something"* — that
is the line that gets you through.

---

## 4. Today's reading order (by time available)

**If you have 60 minutes:**
1. `16-ROUND2-CHEATSHEET.md` (10 min)
2. `12-PROJECT-STORY.md` — rehearse the 3-minute pitch **out loud, twice** (20 min)
3. `14-RAPID-FIRE.md` (20 min)
4. `13-BEHAVIORAL.md` — top 5 STAR stories (10 min)

**If you have 3 hours:** add `01-BIGQUERY.md`, `04-COMPOSER-AIRFLOW.md`,
`11-SYSTEM-DESIGN.md` (do the first design out loud), `06-SQL.md`.

**If you have the day:** work straight through 01 → 15, and do the full mock in
`15-MOCK-INTERVIEW.md` against a clock.

**Last 30 minutes before the call:** *only* the cheat sheet and the project pitch.
No new material. Cramming new facts 20 minutes out degrades recall of what you
already know.

---

## 5. Logistics that quietly decide interviews

- **Have the repo open in a second window.** If they offer screen share, sharing
  `README.md` and walking the architecture diagram is the highest-leverage 5
  minutes available to you. Offer it: *"I have the repo here — would it help if I
  shared the architecture?"*
- **Have a pen and paper visible.** Write while they describe a scenario. It reads
  as structured thinking and buys you 5 seconds before answering.
- **Wired earphones, camera on, plain background, face lit from the front.**
- **Test the platform 15 minutes early** (Teams/Zoom — HCL usually Teams).
- **Water within reach.** A 60-minute panel dries you out and a cracking voice reads as nerves.

---

## 6. The first 90 seconds (write your own version, memorise the shape)

Do not narrate your CV chronologically. Lead with the shape of your value.

> "I'm a data engineer with 5+ years, mostly building batch and streaming pipelines
> on GCP — BigQuery as the warehouse, Dataflow and Pub/Sub for movement, Composer
> for orchestration, Python and SQL end to end. The thread through my work is
> marketing and product analytics data: high-volume, messy, restated-after-the-fact
> source data where the hard part is grain and identity, not throughput. Most
> recently I built an ingestion and attribution platform joining ad-platform spend
> to site-side GA4 tracking in BigQuery — metadata-driven DAG generation, MERGE-based
> restatement handling, and reconciliation checks that fail loudly instead of quietly
> loading zero rows. Before that [previous role]. I'm looking for a role where I own
> the platform rather than individual jobs, which is why this one interested me."

**Why this works:** it states the stack (JD keyword match), states a *theme* (seniority),
names a concrete system (credibility), and closes on motivation (fitment). It also
plants three hooks — *metadata-driven*, *MERGE-based restatement*, *fail loudly* —
that a good interviewer will pull on. You want them pulling on hooks you chose.

---

## 7. Failure modes to actively avoid

1. **Answering the question they didn't ask.** Listen for the *verb*: "explain" vs
   "compare" vs "debug" vs "design" are four different answer shapes.
2. **Over-answering.** If they ask "what's a partition in BigQuery," they want 30
   seconds, not 4 minutes on clustering, materialised views and BI Engine. Save it —
   they'll ask.
3. **Going silent in a scenario question.** Think out loud. *"Okay — first thing I'd
   check is whether the data is missing or just not visible…"* Silence is scored as
   "couldn't do it."
4. **Defending a mistake.** If they correct you and they're right: *"You're right,
   I had that backwards — [correct version]."* Recovering cleanly scores higher
   than never being wrong.
5. **Not asking anything at the end.** See §8.

---

## 8. Your questions for them (ask 2–3, not 6)

Pick by what you actually want to know. These are calibrated to sound like a
Platform Engineer III, not a candidate:

- "Is this a migration engagement or steady-state platform ownership? The day-to-day
  is quite different."
- "Where does transformation live today — BigQuery ELT with dbt, or Dataflow/Dataproc
  before the warehouse?"
- "How is data quality enforced right now — contracts and tests in the pipeline, or
  detection downstream?"
- "What pages the on-call most often?" *(This one impresses. It says you've been on-call.)*
- "How big is the pod, and is there a junior layer I'd be expected to bring up?"
  *(Signals you read the JD — coaching is explicitly in it.)*
- "Who's the client and how direct is the engagement — do engineers join requirement
  gathering, or does that sit with the BA layer?"

**Do not ask** about salary, notice period, WFH, or appraisal cycle in L2. That's L3/HR.

---

## 9. Closing line

When they ask "any questions / anything to add":

> "Only that the JD lines up unusually well with what I've been doing — GCP-native
> batch and streaming, Composer orchestration, and the data quality side, which is
> the part I care most about. If it's useful I'm happy to walk through the pipeline
> repo I mentioned in more detail offline."

Short, confident, gives them a reason to advance you.
