# Behavioural, communication & the Platform Engineer III bar

The JD's soft-skill list is unusually explicit: *strong communication & presentation,
analytical client-first mindset, leadership & stakeholder management, global fast-paced
environment*, plus **coaching junior data engineers** and **solution decks / client meetings
/ requirement gathering**.

At a services firm this is not filler. The level above yours is client-facing. They are
deciding whether they can put you in front of a client.

---

## 1. STAR, tightened

**Situation** (1 sentence — context only) → **Task** (1 sentence — *your* responsibility)
→ **Action** (the bulk — what *you* did, decisions and trade-offs) → **Result** (a number,
and what changed afterwards).

Two rules most people break:
- **"We" is a red flag.** Interviewers are trying to work out what *you* did. Say "I".
- **End with the systemic change**, not just the fix. "…and we added a check so it can't
  recur" is the senior ending.

---

## 2. Prepare these eight stories. Write one line of notes for each now.

| # | Story | What it proves |
|---|---|---|
| 1 | A production incident you diagnosed and fixed | Debugging under pressure |
| 2 | A performance or cost optimisation, with before/after numbers | Commercial impact |
| 3 | A time you disagreed with a stakeholder or an architect | Backbone + diplomacy |
| 4 | A time you coached a junior engineer | **Explicitly in this JD** |
| 5 | A mistake you made and what changed because of it | Self-awareness, no defensiveness |
| 6 | Requirements that were vague, and how you got to clarity | Client-first mindset |
| 7 | A deadline you were going to miss, and how you handled it | Stakeholder management |
| 8 | Something you learned quickly because the project needed it | "Eager to learn new GCP services" |

---

## 3. Model answers — adapt to your own facts

**"Tell me about a production incident."**
> **S** — A marketing fact table had been quietly under-reporting conversions for about ten
> days before anyone noticed. **T** — I owned the pipeline and had to find out how far back
> it went and whether anything downstream had been reported on it.
> **A** — I worked backwards from the sink. The DAG was green every day, so my first
> hypothesis was that a task was succeeding while doing nothing. I compared row counts per
> partition against the source and found the load was correct but the *window* was wrong —
> the restatement pull wasn't wide enough for the platform's actual settlement behaviour,
> so late-revised conversions were never picked up. I widened the window, backfilled the
> affected partitions — which was safe precisely because the load MERGEs on a business key,
> so re-running was a no-op on the rows that were already right — and reconciled against
> the platform UI before telling anyone it was fixed.
> **R** — Restated ten days of data in one run. But the real outcome was the change that
> came out of it: the pipeline was green while being wrong, so I added a reconciliation
> check comparing the platform's own totals against ours as a **blocking gate** before the
> marts build. The class of bug where a pipeline succeeds while loading incomplete data is
> the one that actually costs clients money, because nothing alerts and the dashboards keep
> rendering.

**"Tell me about coaching a junior engineer."** *(prepare this one properly — it's in the JD)*
> **S** — A junior engineer joined the pod and was struggling with the pipelines — not with
> Python, but with why things were built the way they were.
> **T** — Getting them productive was explicitly part of my role, and honestly it was also
> self-interest: I was the single point of failure on the platform.
> **A** — Three things. First, I stopped answering questions with answers and started
> answering with the diagnostic — "here's how I'd find out" rather than "it's the partition
> filter" — which is slower for a fortnight and much faster after that. Second, I gave them
> ownership of a real, small, visible thing rather than tickets off the bottom of the
> backlog: they owned the data quality checks end to end, which meant they had to
> understand the models to write meaningful ones. Third, I put the *why* in writing — my
> READMEs document the design decisions and the rejected alternatives, not just the
> commands, because most handovers fail on the why, not the what.
> **R** — Within about two months they were taking incidents on their own and reviewing my
> PRs with substantive comments. I stopped being the bottleneck, which is the actual point.
> The thing I'd do differently is that I under-communicated the *standard* early on — I
> reviewed their first few PRs too gently and then had to raise the bar later, which is
> harder than setting it correctly at the start.

**"Tell me about a disagreement."**
> **S** — A stakeholder wanted a single blended "true" conversion number combining the ad
> platform's attribution, the analytics tool's, and the CRM's. **T** — I had to either
> build it or explain why not. **A** — I built a comparison first rather than arguing in
> the abstract: I showed the three numbers side by side across a month and how far apart
> they were, and explained *why* — different attribution models and different observation
> points, not a data bug. My position was that a blended number is unfalsifiable: when
> someone challenges it you have no way to explain the discrepancy, and that's how a
> reporting layer loses its credibility permanently. I proposed keeping them as separate
> labelled columns with the variance exposed, plus one **designated primary** metric for
> budget decisions so people still had a single number to act on.
> **R** — They took the compromise. What convinced them wasn't the argument, it was seeing
> the three numbers. I've since defaulted to that: when a stakeholder and I disagree about
> data, I try to make it a question about evidence rather than a question about opinion.

**"Tell me about a mistake."**
> Pick a real one with a real cost, own it in one sentence with no hedging, and spend the
> rest on what changed. **Bad:** "I'm a perfectionist." **Bad:** a mistake that was someone
> else's fault. **Good:** "I deployed a schema change that broke a downstream dashboard
> because I'd checked who queried the *table* but not who queried the *view* on top of it.
> Two hours of a broken exec dashboard. What changed: I use lineage now rather than my own
> memory of who depends on what, and additive-only changes with a deprecation window for
> anything breaking."

**"Vague requirements."**
> "The request is usually a solution, not a requirement — 'I need a dashboard with these
> columns.' I try to get one level up: what decision does this let you make, and what would
> you do differently if the number came back high versus low? If they can't answer that
> second question, the metric usually isn't the right one yet. I'll also ask what they do
> *today* without it, because the existing spreadsheet tells you the real business logic
> faster than any requirements document. Then I write it back to them as a one-pager —
> grain, definitions, refresh frequency, and what's explicitly out of scope — and get that
> confirmed before building. The out-of-scope list prevents more rework than anything else."

---

## 4. The standard questions and their traps

- **"Why are you leaving?"** — Forward-looking, never critical of the current employer.
  *"I've taken the platform there about as far as the scope allows; I want ownership of a
  broader platform and more direct client exposure."*
- **"Why HCL?"** — Scale and variety of client engagements, exposure to greenfield GCP
  builds and migrations rather than one steady-state platform, the Noida location works.
  Mention something specific from the JD — the data quality and governance ownership, or
  the coaching element — so it's not generic.
- **"Where do you see yourself in 3–5 years?"** — Architect/lead track: owning solution
  design and being in the room for requirement gathering, which the JD already mentions.
- **"Your weakness?"** — A real one with a mitigation in progress. *"I default to building
  the robust version when the situation only needed the quick one. I've started explicitly
  asking whether something is a throwaway or a foundation before I start."*
- **"Rate yourself out of 10 on SQL/Python/GCP."** — **Never say 9 or 10.** Say 8 and
  qualify it: *"8 — strong on analytical SQL, window functions, modelling and optimisation;
  I'd want more depth on query plan internals at very large scale."* A calibrated answer
  reads as senior; a 10 invites them to prove you wrong.
- **"How do you keep up with GCP?"** — Release notes, the Google Cloud blog, building small
  things. Name one thing you learned recently (BigQuery Iceberg tables, Dataflow Prime,
  dataset-driven scheduling in Airflow) — specificity proves it's true.
- **"Are you comfortable with client calls / a global team?"** — Yes, with an example.
  Mention comfort with overlapping hours if you have it; HCL engagements are often US/EU-facing.
- **Notice period / location / compensation** — answer factually and briefly. Don't
  negotiate in L2; that's HR's round.

---

## 5. Communication mechanics that get scored

- **Answer the question asked, then stop.** Silence after a complete answer is confidence.
  Filling it is where candidates talk themselves out of a point.
- **Signpost.** *"Three things — first… second… third…"* Panels remember structured answers
  and forget unstructured ones, even when the content is identical.
- **If you don't know:** *"I haven't used Data Fusion in production. What I know is that
  it's the managed CDAP visual builder that compiles to Spark on Dataproc, and I'd reach
  for it where the client needs low-code and many connectors rather than a coding team.
  How is it used on this engagement?"* — bounded honesty + reasoning + curiosity.
  **Never** bluff a number.
- **If you're corrected:** *"You're right, I had that backwards — [correct version]."* Then
  move on. Don't over-apologise; one sentence.
- **If you go blank:** *"Let me think about that for a second."* Then think. Out loud, if
  it helps: *"Okay — the first thing I'd check is…"*
- **Pace.** Nerves make everyone speak 20% faster. Deliberately slow down and breathe at
  full stops. On a call, a small pause before answering reads as considered, not slow.
- **Ask a clarifying question on scenario questions.** Every time. It's free marks.
