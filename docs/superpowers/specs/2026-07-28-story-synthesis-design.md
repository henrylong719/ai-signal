# Story Synthesis pipeline — design

## Problem

AI Signal ingests ~336 curated sources into a single flat `articles`
table. When a real event happens — a model launch, a funding round, a
paper — dozens of sources cover it, and today each one is an independent
row. The feed, the digest, and For You all treat those as N unrelated
articles. The product's own promise ("find the signal in the noise")
is only half-delivered: we *rank* the noise well, but we never
*collapse* it.

We also use AI only for ranking (OpenAI `text-embedding-3-small`,
384-dim, in `services/embeddings.py`). Nothing in the reader-facing
experience is generated: no per-article TL;DR, no synthesized "what
happened and why it matters," no cross-source deduplication.

This spec adds a **Story Synthesis** layer: cluster the same event
across sources into one *Story*, then use Claude to synthesize a
grounded, cited summary of that Story. It is the flagship AI/ML feature
— the demo is "40 duplicate headlines → 1 synthesized, cited story
card" — and it is built to be *evaluated*, not just shipped.

## Goals / non-goals

**Goals**
- Incrementally cluster articles into Stories as they are ingested
  (streaming, not a nightly batch), reusing the embeddings we already
  compute during ingest.
- Synthesize each Story with Claude into `{headline, what_happened,
  why_it_matters, claims[]}`, where every claim cites the member
  article(s) that support it (grounding against hallucination).
- Ship an **evaluation harness** with real metrics (clustering quality
  + summary groundedness) reported in the README — this is the part
  that makes it a portfolio piece rather than a demo.
- Expose Stories through a read API and surface them in the digest /
  a story-detail view, including a guest-visible before/after.

**Non-goals (explicitly deferred)**
- Monetization, SEO story pages, share loops, alerts, PWA — out of
  scope for this milestone (see the portfolio framing: depth on one
  feature beats breadth).
- Re-clustering historical articles beyond a bounded backfill window.
- Multi-lingual synthesis. English sources only for v0.

## Decisions

- **Online incremental clustering, not nightly k-means.** Each newly
  ingested article either joins the nearest existing *recent* Story
  (cosine ≥ threshold against the Story centroid) or seeds a new Story.
  This mirrors how the data actually arrives (a stream of RSS items)
  and is a stronger ML-engineering talking point than a batch
  re-cluster. Centroids are stored on the Story so attachment is a
  single pgvector nearest-neighbor query, not an all-pairs scan.
- **Time-boxed clustering.** A Story only accepts new members within a
  rolling window (default 72h from the Story's first article). Two
  articles about "GPT releases" three weeks apart are different stories.
  This also bounds the candidate set for attachment.
- **Synthesis is grounded and structured.** Claude receives only the
  member articles' `title` + `excerpt` + `source`, and must emit a
  fixed JSON schema (structured outputs) where each claim references
  the source index(es) it is drawn from. The prompt forbids claims not
  supported by the provided text. This is the anti-hallucination
  contract the eval measures.
- **Synthesis is triggered, not per-article.** A Story is (re)synthesized
  when it is "settled" — it has ≥ `MIN_CLUSTER_SIZE` members and hasn't
  gained a member in `SYNTH_QUIET_MINUTES`, or it is about to be served
  in a digest. Avoids re-calling Claude on every RSS tick.
- **Default synthesis model: `claude-opus-4-8`.** Highest-quality
  grounding for the flagship surface. `claude-sonnet-5` is the cost
  lever if daily volume makes Opus too expensive — that is a cost
  decision for the operator, exposed via `SYNTHESIS_MODEL`, not a
  default we pick to save money.
- **Additive, not a rewrite.** Articles keep flowing through the
  existing feed unchanged. A `story_id` FK is nullable; an un-clustered
  article behaves exactly as today. The digest gains an optional
  story-backed section but its existing sections still work.

## Data model

Two new tables + one nullable FK on `articles`. Alembic migration
chained onto the current head (currently
`e4f5a6b7c8d9_add_degraded_ingest_status`; confirm with
`alembic heads` before setting `down_revision`).

### `stories`

| column | type | notes |
|---|---|---|
| `id` | uuid pk | |
| `centroid` | `Vector(384)` nullable | running mean of member embeddings; `EMBEDDING_DIM` from `models/article.py` |
| `member_count` | int | denormalized; drives synthesis trigger + display |
| `lead_article_id` | uuid fk → articles.id | highest-scored member, for the card image/link |
| `first_article_at` | timestamptz | window anchor (clustering cutoff = this + `STORY_WINDOW`) |
| `last_member_at` | timestamptz | drives the "quiet" synthesis trigger |
| `category` | str(32) | majority category of members (reuses `Category`) |
| `status` | enum `pending` \| `synthesized` \| `failed` | synthesis lifecycle, mirrors `ingest_run` status style |
| `synthesized_at` | timestamptz nullable | idempotency watermark for re-synthesis |
| `created_at` / `updated_at` | timestamptz | |

Synthesized content (nullable until `status = synthesized`):

| column | type | notes |
|---|---|---|
| `headline` | text | Claude-written, ≤ ~90 chars |
| `what_happened` | text | 2–3 sentences |
| `why_it_matters` | text | 1–2 sentences |
| `claims` | JSONB | `[{text, source_article_ids: [uuid, ...]}]` — the grounding record |
| `synthesis_model` | str | which model produced it (audit / eval) |
| `synthesis_input_tokens` / `synthesis_output_tokens` | int | cost telemetry, surfaced in the README |

Index: ivfflat/hnsw on `centroid` (same extension already enabled for
`articles.embedding`) so attachment is a fast ANN lookup, plus a btree
on `(status, last_member_at)` for the synthesis worker's scan.

### `articles.story_id`

Nullable uuid FK → `stories.id`, `ON DELETE SET NULL`, indexed. NULL =
not yet clustered (cold path, behaves as today). No backfill in the
migration; a bounded backfill script handles existing rows (see
Milestone 5).

> Why a FK on `articles` rather than a join table: membership is
> 1-article-to-1-story and queried "give me this story's articles" and
> "what story is this article in" — both are single-column lookups. A
> join table would add a hop for no cardinality we need.

## Services

New modules, following the existing `services/` conventions (module
docstring explaining *why*, dependency-injection seam for tests like
`embeddings.set_encoder_for_testing`).

### `services/clustering.py`

Pure-ish clustering logic, no Claude.

- `attach_or_create_story(session, article) -> Story` — for one
  embedded article: ANN query for candidate Stories whose
  `first_article_at` is within `STORY_WINDOW` of `article.published_at`;
  take the nearest by cosine (reuse `embeddings.cosine_similarity`); if
  `sim >= CLUSTER_THRESHOLD`, join it and update the centroid
  incrementally (running mean → re-`_l2_normalize`), else create a new
  Story seeded by this article. Updates `member_count`,
  `last_member_at`, `lead_article_id`, `category`.
- `recompute_centroid(story)` — exact recompute (used by the backfill
  and as a correctness check against the incremental update; the eval
  harness asserts they agree within tolerance).

Threshold selection is an ML decision, not a magic number: the eval
harness (Milestone 4) sweeps `CLUSTER_THRESHOLD` against the labeled
set and the chosen value + its F1 go in the README.

### `services/synthesis.py`

The Claude integration. Uses the official Anthropic Python SDK
(`anthropic`), matching the OpenAI-via-httpx pattern in
`embeddings.py` but with the first-party SDK.

- `LLMClient` Protocol + `_AnthropicClient` (real) + a
  `set_client_for_testing()` seam mirroring
  `embeddings.set_encoder_for_testing` — so tests never hit the network.
- `synthesize_story(session, story) -> Story` — loads member articles,
  builds the grounded prompt (member `title`/`excerpt`/`source` as a
  numbered list), calls Claude with **structured outputs**
  (`output_config.format` json_schema) so the response validates to
  `{headline, what_happened, why_it_matters, claims:[{text,
  source_indexes:[int]}]}`. Maps `source_indexes` back to article UUIDs,
  writes the columns, stamps `synthesized_at`, sets
  `status = synthesized`, records token usage. Per-story failure isolation:
  on error, `status = failed` + logged, never raises into the caller
  (same philosophy as `ingest_runner`'s degraded handling).

Model call shape (grounding is enforced in the system prompt + schema):

```python
resp = client.messages.create(
    model=settings.SYNTHESIS_MODEL,   # "claude-opus-4-8" default
    max_tokens=1500,
    thinking={"type": "adaptive"},
    system=GROUNDING_SYSTEM_PROMPT,   # "only claims supported by the
                                      #  provided articles; cite indexes"
    output_config={"format": {"type": "json_schema", "schema": STORY_SCHEMA}},
    messages=[{"role": "user", "content": rendered_members}],
)
```

### `services/story_runner.py`

The orchestration wrapper, mirroring `ingest_runner.run_tracked_ingest`:

- Called at the **end of** `run_tracked_ingest` (after new articles +
  their embeddings are committed): cluster the just-inserted articles,
  then synthesize any Stories that became "settled."
- Opens its own short-lived sessions; failures are logged and swallowed
  so a synthesis outage never breaks ingestion.

## Config (`core/config.py`)

Additive settings, following the existing `OPENAI_*` / `*_ENABLED` /
`*_HOUR_UTC` conventions:

```python
ANTHROPIC_API_KEY: str | None = None
SYNTHESIS_ENABLED: bool | None = None      # None → derive from env like INGEST_SCHEDULER_ENABLED
SYNTHESIS_MODEL: str = "claude-opus-4-8"
CLUSTER_THRESHOLD: float = 0.62            # tuned by the eval harness; placeholder
STORY_WINDOW_HOURS: int = 72
MIN_CLUSTER_SIZE: int = 3                  # synthesize only real clusters
SYNTH_QUIET_MINUTES: int = 30
```

Synthesis short-circuits (logs + no-op) when `ANTHROPIC_API_KEY` is
unset — same defensive pattern as `RESEND_API_KEY` in the digest path,
so local dev without a key still runs.

## API + frontend surface

- `GET /api/v1/stories/` — recent synthesized Stories (paginated),
  each with `headline`, `what_happened`, `why_it_matters`,
  `member_count`, `lead_article` (as `ArticlePublic`), and the cited
  claims. Rate-limited like the other feed routes.
- `GET /api/v1/stories/{id}` — one Story with its full member list.
- Digest: `build_digest` gains an optional lead "Top stories, synthesized"
  section sourced from Stories when available, falling back to the
  current computed sections. Anonymous/guest requests can see it — this
  is the before/after demo surface.
- Frontend: a `StoryCard` (headline + why-it-matters + "covered by N
  sources" + expandable member list with per-claim citations). Reuses
  the existing article-card styling. Regenerate the TS client
  (`scripts/generate-client.sh`) after the routes land.

## Evaluation harness — the portfolio centerpiece

Lives in `backend/app/eval/` + a small labeled fixture set. Runnable
offline (no scheduler), deterministic, and its numbers go in the README.

### Clustering quality
- Hand-label ~50–100 articles from one representative week into gold
  clusters (`eval/fixtures/gold_clusters.jsonl`).
- `eval/clustering_eval.py`: run `clustering.attach_or_create_story`
  over the fixture embeddings, compute **pairwise precision/recall/F1**
  and **homogeneity / completeness / V-measure** vs. gold.
- Sweep `CLUSTER_THRESHOLD` ∈ {0.50 … 0.75}; emit a small table; the
  chosen threshold + its F1 are committed to the README.

### Summary groundedness
- `eval/groundedness_eval.py`: for each synthesized Story, an
  LLM-as-judge pass (default `claude-opus-4-8`; `claude-haiku-4-5` is
  the cheaper judge option the operator can select) scores each claim
  as supported / unsupported by the cited articles. Report
  **% claims grounded** and dump the unsupported examples for the
  failure analysis section.
- A cheap deterministic guardrail alongside the judge: assert every
  `claims[].source_article_ids` actually points at real members
  (schema-level grounding can't hallucinate a citation, but the mapping
  code can have bugs).

### Cost / latency
- `eval/cost_report.py`: aggregate `synthesis_input_tokens` /
  `synthesis_output_tokens` across a run → tokens per Story, $ per daily
  run (both models), p50/p95 synthesis latency. README line:
  "clustering F1 X; Y% of claims grounded; $Z/day at N stories."

## Testing

Per project convention: `POSTGRES_PORT=5433` against the
`ai-signal-test-db` container, run via `backend/.venv` (see
`[[use-backend-venv-not-uv-run]]`). TDD, milestone by milestone.

- `clustering`: fake embeddings (deterministic vectors) → assert
  attach-vs-seed decisions, window cutoff, centroid running-mean
  correctness vs. `recompute_centroid`.
- `synthesis`: `set_client_for_testing()` with a fake `LLMClient`
  returning canned structured JSON → assert column writes, index→UUID
  mapping, failure isolation (`status = failed`, no raise), token
  recording. No network.
- `story_runner`: end-to-end with fakes for both encoder and LLM →
  ingest → cluster → synthesize, assert idempotency (re-run doesn't
  double-synthesize a settled Story).
- routes: `GET /stories` shape, pagination, rate limiting.

## Milestones (TDD, each independently shippable)

1. **Data model** — `stories` table, `articles.story_id`, migration,
   model classes, CRUD stubs. Green tests for the schema + basic CRUD.
2. **Clustering** — `services/clustering.py` + incremental centroid;
   wire into `run_tracked_ingest`. No Claude yet; Stories form but stay
   `pending`.
3. **Synthesis** — `services/synthesis.py` with the Anthropic SDK +
   structured outputs + the testing seam; `services/story_runner.py`
   triggers on settled Stories.
4. **Eval harness** — labeled fixtures + clustering/groundedness/cost
   scripts; commit the numbers to the README. *This is the milestone
   that makes it a portfolio piece — don't skip or shrink it.*
5. **Backfill + API + frontend** — bounded backfill over recent
   articles, `/stories` routes, `StoryCard`, digest integration,
   regenerate the TS client. Guest before/after demo.

## Open questions

- Story merge/split: two Stories that drift together (or one that
  should split) aren't handled in v0 — incremental clustering can't
  merge after the fact. Acceptable for the demo; note it as "known
  limitation + future work" in the README (good interview material:
  online clustering's fundamental tradeoff).
- Lead-article selection: reuse the digest's ranking, or simplest
  (earliest / most-sources-agreeing)? Start simple; revisit if the eval
  shows poor lead choices.
