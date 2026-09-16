# Python for the data engineering round

Reported HCL rounds include **"medium-level Python coding."** That means: string/dict
manipulation, a little pandas, a generator, an API client with retries, and a "write this
function" whiteboard exercise. Not LeetCode hard.

---

## 1. Language questions they actually ask

**`list` vs `tuple` vs `set` vs `dict`** — mutable ordered / immutable ordered (hashable,
so usable as a dict key) / unordered unique, O(1) membership / hash map, insertion-ordered
since 3.7.

**Mutable default argument — the classic trap**
```python
def add(x, acc=[]):     # BUG: acc is created once, at function definition
    acc.append(x); return acc
add(1); add(2)          # -> [1, 2]

def add(x, acc=None):   # fix
    acc = [] if acc is None else acc
```

**Shallow vs deep copy** — `copy.copy` copies the container, `copy.deepcopy` copies
recursively. Matters when config dicts are shared across generated DAGs (yours!).

**Generators vs lists** — `yield` produces lazily, constant memory.
> "Reading a 20 GB extract line by line with a generator keeps memory flat; building a
> list materialises all of it. In a DoFn or an Airflow task with a fixed worker size,
> that's the difference between running and OOM-killing the pod."

```python
def read_batches(path, size=10_000):
    batch = []
    with open(path) as fh:
        for line in fh:
            batch.append(json.loads(line))
            if len(batch) == size:
                yield batch; batch = []
    if batch: yield batch
```

**Decorators** — a function that wraps a function. Be able to write `@retry`:
```python
import functools, random, time

def retry(times=3, base=1.0, exceptions=(Exception,)):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            for attempt in range(times):
                try:
                    return fn(*a, **kw)
                except exceptions:
                    if attempt == times - 1:
                        raise
                    sleep = random.uniform(0, base * 2 ** attempt)   # full jitter
                    time.sleep(sleep)
        return wrapper
    return deco
```
**Say why full jitter:** *"Un-jittered exponential backoff makes every parallel worker
retry in lockstep and reproduces the thundering herd that caused the throttle. Full jitter
spreads them. I use exactly this in my Meta connector."*

**Context managers** — `with`, `__enter__`/`__exit__`, `contextlib.contextmanager`.
Guarantees cleanup on exception. "Why `with open(...)`" → deterministic close.

**`*args` / `**kwargs`**, **list/dict comprehensions**, **`lambda`**, **`map`/`filter`**,
**f-strings**, **`enumerate`/`zip`**, **`collections.defaultdict` / `Counter`**,
**`itertools.groupby`** (requires pre-sorted input — a classic gotcha).

**GIL** — one thread executes Python bytecode at a time, so threads help **I/O-bound**
work (API calls, GCS reads) but not CPU-bound. For CPU-bound, use `multiprocessing` or
push the compute into BigQuery/Beam. *"In data engineering the honest answer is that I
don't parallelise CPU in Python — I let BigQuery or Dataflow do it."*

**`__init__` vs `__new__`**, **`@staticmethod` vs `@classmethod`**, **ABCs** — relevant
because your `base.py` defines the `Connector` contract:
```python
from abc import ABC, abstractmethod

class Connector(ABC):
    @property
    @abstractmethod
    def merge_keys(self) -> list[str]: ...
    @abstractmethod
    def schema(self) -> list[dict]: ...
    @abstractmethod
    def extract(self, start, end): ...
```
> "Making the contract explicit means adding Google Ads is implementing three methods —
> the loader, orchestration and freshness checks are source-agnostic and don't change."

**Type hints / dataclasses / pydantic** — mention that you type-annotate and validate
config; `mypy`/`ruff` in CI.

**`is` vs `==`**, **truthiness of `[]`/`0`/`None`**, **exception hierarchy** (catch
`Exception`, never bare `except:`), **EAFP vs LBYL**.

---

## 2. Coding problems with a data-engineering flavour

**a) Deduplicate keeping the latest version**
```python
def latest_by_key(records, key="id", ts="updated_at"):
    out = {}
    for r in records:
        if key not in out or r[ts] > out[r[key]][ts]:
            out[r[key]] = r
    return list(out.values())
```
Then say: *"In SQL I'd do this with `QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY
updated_at DESC) = 1` and push it into the warehouse — one pass, no memory in my process."*
**Always bridge the Python answer back to the SQL answer.** It shows you know where work belongs.

**b) Flatten a nested dict** (JSON → BigQuery columns)
```python
def flatten(d, parent="", sep="_"):
    out = {}
    for k, v in d.items():
        key = f"{parent}{sep}{k}" if parent else k
        if isinstance(v, dict):
            out.update(flatten(v, key, sep))
        elif isinstance(v, list):
            out[key] = json.dumps(v)      # or explode, depending on the grain you want
        else:
            out[key] = v
    return out
```

**c) Word / event frequency, top N**
```python
from collections import Counter
import heapq
Counter(events).most_common(5)                     # or heapq.nlargest(5, c.items(), key=lambda kv: kv[1])
```

**d) Find duplicates / missing dates in a series**
```python
dates = {r["date"] for r in rows}
expected = {start + timedelta(days=i) for i in range((end - start).days + 1)}
missing = sorted(expected - dates)          # gap detection for a freshness check
```

**e) Chunk a list** (for batched API calls / BigQuery load sizing)
```python
def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]
```

**f) Two sums / anagram / reverse a string / fibonacci** — if they throw a light DSA
question, these are the likely ones. Know `dict`-based two-sum in O(n).

**g) Read a large CSV and aggregate without pandas**
```python
import csv
from collections import defaultdict
totals = defaultdict(float)
with open(path, newline="") as fh:
    for row in csv.DictReader(fh):
        totals[row["campaign_id"]] += float(row["spend"])
```

---

## 3. Pandas (asked, but keep it in proportion)

```python
df.groupby("campaign_id", as_index=False).agg(spend=("spend", "sum"),
                                              clicks=("clicks", "sum"))
df.merge(other, on="ad_id", how="left", indicator=True)      # _merge tells you what didn't match
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("updated_at").drop_duplicates("id", keep="last")
df.pivot_table(index="date", columns="channel", values="spend", aggfunc="sum")
df.fillna(0) / df.dropna(subset=["ad_id"])
pd.read_csv(path, chunksize=100_000)                          # memory-bounded read
```

**The senior framing:** *"I use pandas for exploration and for small-to-medium
transforms inside a task, but I don't build pipelines on it — it's single-machine and
in-memory, so it becomes the scaling ceiling. If it doesn't fit comfortably in a worker,
that's a signal the transform belongs in BigQuery SQL or Beam. I've seen more production
incidents from a pandas step silently growing past the worker's memory than from anything else."*

`merge` `how=` semantics, `apply` being slow (row-wise Python) vs vectorised ops, and
`SettingWithCopyWarning` (use `.loc`) are the standard follow-ups.

---

## 4. The engineering-practice questions (Platform Engineer III territory)

**"How do you test a data pipeline?"**
> Four layers.
> 1. **Unit tests** on the transform functions and the client — I mock the HTTP layer and
>    assert on behaviour, not on the API. My connector has 15 tests that run with no
>    credentials, including one that covers a specific Meta quirk: `async_percent_completion`
>    hits 100 *before* `async_status` flips to `Job Completed`, so treating 100% as done
>    gives you an empty result set. That test exists because that bug is invisible until
>    production.
> 2. **DAG integrity tests** — import the DagBag in CI, assert no import errors, assert
>    every DAG has owner/retries/SLA/tags.
> 3. **Data tests** — dbt tests or `BigQueryCheckOperator` gates between load and marts:
>    uniqueness on the grain, not-null on keys, referential integrity, freshness, and
>    row-count deltas against the prior partition.
> 4. **Reconciliation** — for anything migrated or dual-run, compare counts, checksums and
>    business aggregates against the source of truth before cutover.

**"How do you structure a Python project?"**
`src/` layout, `pyproject.toml`, editable install, `ruff` + `black` + `mypy`,
`pytest` with fixtures, no logic in `__init__.py`, config out of code (YAML + env),
secrets from Secret Manager. Point at this repo — it does exactly that.

**"Logging?"** — `logging` module not `print`, structured JSON logs so Cloud Logging
parses fields, correlation/run ID on every line, never log tokens or PII.
`logger.exception()` inside the except block to keep the traceback.

**"How do you handle secrets?"** — Secret Manager + Workload Identity / service account
impersonation. **Never** a key file on disk, never in Airflow Variables in plaintext,
never in the repo. `.env.example` with placeholder values, `.env` gitignored — which is
what this repo does.
