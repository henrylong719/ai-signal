# Editor Agent — design

## Problem

AI Signal already personalizes: it computes a user interest vector,
tracks saved / clicked / dismissed signals, and ranks a "For You" feed
(`services/for_you.py`, `services/recommender.py`). But personalization
today is *ranking* — the product orders articles and stops. It never
**reasons about what matters to this user and acts on it.**

A generic "chat over the articles" agent would be pointless: Google and
ChatGPT-with-search do open-web Q&A better, because they have the whole
web. An agent is only worth building where a stateless public search box
*structurally cannot* go. AI Signal owns exactly that ground:

1. **Private signals** — the user's interest vector, saved/dismissed
   history. Google has none of this.
2. **A curated corpus** — ~336 vetted sources, not the SEO web; soon
   deduplicated into Stories.
3. **The user's account** — an agent with tools can *save an article,
   tune interest tags*. Google can only tell you things; it can't act.

This spec adds an **Editor agent**: a tool-using agent that reads the
user's private signals, searches the curated corpus, decides what is
worth *their* attention, drafts a short cited briefing, and — with
explicit approval — takes account actions. It is the flagship *agentic*
feature (multi-step, tool-driven, autonomous relevance judgment + gated
side effects), and the deliberate companion to Story Synthesis rather
than a competitor: when Stories ship, the Editor reads them.

## Goals / non-goals

**Goals**
- A real **agent loop** (Anthropic SDK tool runner): the model chooses
  which tools to call and when to stop — not a single prompt→JSON call.
- Ground every briefing claim in the corpus with `[article_id]`
  citations; refuse rather than invent when coverage is thin.
- **Gated side-effecting actions** — `save_article`, `set_interest_tags`
  never fire silently; they require a human-in-the-loop approval step.
  This gating pattern is the core agentic-AI craft the feature teaches.
- Reuse the existing personalization + search services unchanged; the
  agent is additive, behind a new route, and off by default.
- Ship an **evaluation harness** for agent quality (did it pick the
  right things? did it stay grounded? did it respect the approval gate?)
  — mirroring the Story Synthesis spec's eval-as-centerpiece framing.

**Non-goals (explicitly deferred)**
- `follow_source` as an action: there is **no followed-source model or
  CRUD in the codebase today** (the README mentions "followed sources"
  but nothing backs it). Adding that table is out of scope; the tool is
  listed as a future action, not built in v0.
- Autonomous / scheduled runs (a daily push briefing). v0 is
  on-demand, user-initiated. A scheduled variant is future work.
- Multi-turn conversation memory across sessions. Each run is one
  briefing request.
- Streaming the agent's intermediate steps to the UI (nice-to-have;
  v0 returns the finished briefing).

## Decisions

- **Tool runner, not a hand-written loop.** Use the Anthropic Python
  SDK's `client.beta.messages.tool_runner` with `@beta_tool`-decorated
  functions. It drives the request→execute→re-send cycle; we write only
  the tool functions. Rationale: the loop *is* the thing being learned,
  and the runner lets us focus on tool design + the approval gate rather
  than plumbing. Model `claude-opus-4-8` (reuse `SYNTHESIS_MODEL` from
  the Story spec's config).

- **Read tools vs. write tools are a hard split.** Read tools
  (`get_my_signals`, `search_corpus`, `get_recent_feed`) execute
  automatically inside the loop. Write tools (`save_article`,
  `set_interest_tags`) **do not execute during the loop** — they return
  a "proposed, awaiting approval" result, the agent collects proposals,
  and the route surfaces them to the user for one explicit confirm/deny.
  Reversibility is the criterion (same reasoning as promoting an action
  to a dedicated, gate-able tool): reading is safe to auto-run; mutating
  the user's account is not.

- **Grounding is enforced in the system prompt + citations.** The agent
  may only assert what a tool returned, and every briefing item cites
  the `article_id`(s) it rests on. A cheap deterministic guardrail
  asserts each cited id was actually returned by a `search_corpus` /
  `get_recent_feed` call this run — the model can't cite an article it
  never retrieved. This is the same anti-hallucination contract Story
  Synthesis uses, applied to a multi-step loop.

- **Corpus surface is swappable.** v0 reads the live feed via
  `get_recent_feed` (wraps `crud.article.get_articles`). When Story
  Synthesis lands, add a `list_todays_stories` tool over the `stories`
  table; the agent prefers Stories when available and falls back to the
  feed. No rewrite — one more tool in the list.

- **Additive and off by default.** New `services/editor_agent.py`, new
  `POST /api/v1/editor/*` routes, new config flags. Short-circuits to a
  logged no-op when `ANTHROPIC_API_KEY` is unset (same defensive pattern
  as `RESEND_API_KEY`), so local dev without a key still runs.

## Tool surface

New module `services/editor_agent.py`, following existing `services/`
conventions (module docstring explaining *why*, a `set_client_for_testing`
seam mirroring `embeddings.set_encoder_for_testing`).

Each tool is a thin wrapper over an **existing, verified** function.
Tools take a `user_id` bound at construction (closure/partial), not from
the model — the model never chooses whose account it acts on.

### Read tools (auto-execute in the loop)

| Tool | Wraps (verified to exist) | Returns to the model |
|---|---|---|
| `get_my_signals()` | `for_you.build_user_profile(session, user_id)` + `crud.interest.get_interests(...)` + saved titles from `crud.article.get_saved_articles_with_articles(...)` | Interest tags, top saved themes, recently dismissed themes — a compact text profile |
| `search_corpus(query, limit=8)` | `article_search.search_articles(session, query=..., limit=...)` | `[id] title — source — excerpt` lines |
| `get_recent_feed(limit=20)` | `crud.article.get_articles(...)` (latest) | Same line format; the "what's new" surface until Stories exist |

### Write tools (propose-only; gated)

| Tool | Wraps | Loop behavior |
|---|---|---|
| `save_article(article_id, reason)` | `crud.article.save_article(...)` | **Does not save.** Records a proposal `{action: "save", article_id, reason}`, returns `"proposed — awaiting user approval"` to the model |
| `set_interest_tags(add[], remove[], reason)` | `crud.interest.set_interests(...)` | **Does not write.** Records a proposal, returns the same awaiting-approval result |

The tool functions themselves enforce the gate — they append to a
`proposals` list and return the awaiting-approval string rather than
executing. This is the human-in-the-loop pattern done at the tool
boundary (the SDK tool runner runs the function, but the function's job
is to *stage*, not commit).

### Deferred tool

| Tool | Why not in v0 |
|---|---|
| `follow_source(source)` | No followed-source model / CRUD exists in the codebase. Requires a new table + migration first; tracked as future work, not built here. |

## The agent loop

`run_editor(session, user_id) -> EditorBriefing`:

```python
proposals: list[Proposal] = []

runner = client.beta.messages.tool_runner(
    model=settings.EDITOR_MODEL,          # default claude-opus-4-8
    max_tokens=2500,
    system=EDITOR_SYSTEM_PROMPT,          # grounding + gating contract
    tools=[get_my_signals, search_corpus, get_recent_feed,
           save_article, set_interest_tags],   # closures bound to user_id + proposals
    messages=[{"role": "user",
               "content": "Build my briefing for today."}],
)

final = None
for message in runner:      # ← the agentic loop; SDK runs read tools between turns
    final = message
    # (optional) enforce a max-iteration cap here

briefing_text = next(b.text for b in final.content if b.type == "text")
_assert_citations_grounded(briefing_text, retrieved_ids)   # deterministic guardrail
return EditorBriefing(text=briefing_text, proposals=proposals)
```

The system prompt instructs the agent to: call `get_my_signals` first;
search the corpus for what intersects those signals; read enough to
judge relevance; write a short briefing (what matters to *you*, what to
skip, each cited); and *propose* saves / tag changes rather than
assuming them. Response length calibrated by prompt (a briefing, not an
essay).

**Two-phase execution (the gate):**
1. **Phase 1 — `run_editor`** returns the briefing + staged `proposals`.
   Nothing has mutated the account yet.
2. **Phase 2 — `apply_proposals(session, user_id, approved_ids)`** runs
   only the proposals the user confirmed, calling the *real*
   `save_article` / `set_interests` CRUD. Per-proposal failure isolation
   (one bad save doesn't sink the rest), idempotent.

## Config (`core/config.py`)

Additive, following the `*_ENABLED` / `*_MODEL` conventions the Story
spec established (shares `ANTHROPIC_API_KEY`):

```python
EDITOR_AGENT_ENABLED: bool | None = None   # None → derive from env
EDITOR_MODEL: str = "claude-opus-4-8"      # claude-sonnet-5 as cost lever
EDITOR_MAX_ITERATIONS: int = 8             # loop safety cap
EDITOR_SEARCH_LIMIT: int = 8
```

Short-circuits (logs + returns an empty briefing) when
`ANTHROPIC_API_KEY` is unset.

## API + frontend surface

- `POST /api/v1/editor/briefing` (`CurrentUser`) → runs Phase 1, returns
  `{briefing: str, proposals: [{id, action, target, reason}]}`.
  Rate-limited like the other authenticated routes. Nothing is mutated.
- `POST /api/v1/editor/apply` (`CurrentUser`) → body `{approved: [id...]}`
  → runs Phase 2, returns what was applied.
- Frontend: an "Editor" panel — renders the cited briefing, then the
  proposals as a checklist with Approve / Dismiss. Approving posts to
  `/editor/apply`. Reuses existing article-card styling for cited items.
  Regenerate the TS client (`scripts/generate-client.sh`) after routes
  land.

The two-endpoint shape *is* the human-in-the-loop gate made visible:
the agent proposes, the user disposes.

## Evaluation harness — the portfolio centerpiece

Lives in `backend/app/eval/` (alongside the Story Synthesis eval).
Runnable offline, deterministic via a fake `LLMClient`, numbers in the
README. This is what makes it read as agentic-AI *engineering*.

### Grounding
- `editor_eval.py`: assert every `[article_id]` cited in a briefing was
  actually returned by a tool call in that run (deterministic — no
  judge needed). Report **% briefings fully grounded**; dump violations.

### Relevance-to-user
- With a small set of labeled fixture users (interest vector + gold
  "should surface" / "should skip" article sets), run the agent and
  score its picks: **precision/recall of surfaced items vs. gold.**
  This is the "did it pick the right things" question, measurable.

### Gate integrity
- Assert `run_editor` **never mutates** the DB (no save / interest rows
  written in Phase 1) — the safety property, tested directly. A write
  in Phase 1 is a failing test, full stop.

### Cost / latency
- Tool-call count, tokens, p50/p95 per briefing (both models). README
  line: "X% grounded; relevance F1 Y; gate-integrity 100%; $Z/briefing."

## Testing

Per project convention: `POSTGRES_PORT=5433` against `ai-signal-test-db`,
run via `backend/.venv`. TDD, milestone by milestone.

- **tools**: each read tool with a real session + seeded articles →
  assert the returned text shape and that it wraps the right CRUD.
- **gate**: `set_client_for_testing()` with a fake `LLMClient` that
  emits canned `save_article` / `set_interest_tags` tool calls → assert
  Phase 1 stages proposals and writes **nothing**; assert
  `apply_proposals` writes only approved ones, with failure isolation.
- **grounding guardrail**: a briefing citing an un-retrieved id → assert
  the guardrail flags it.
- **loop**: fake `LLMClient` driving search → read → briefing → assert
  idempotency and the max-iteration cap.
- **routes**: `/editor/briefing` and `/editor/apply` shape, auth, rate
  limiting.

## Milestones (TDD, each independently shippable)

1. **Read tools** — `get_my_signals`, `search_corpus`, `get_recent_feed`
   as `@beta_tool` wrappers + the `set_client_for_testing` seam. Green
   tests for tool output shape. No loop yet.
2. **Agent loop (read-only)** — `run_editor` with read tools only;
   produces a cited briefing, no actions. Grounding guardrail + its test.
3. **Gated write tools** — `save_article` / `set_interest_tags` as
   propose-only; `apply_proposals`; the gate-integrity test. *This is
   the milestone that makes it an agent with real, safe side effects —
   don't shrink it.*
4. **Eval harness** — grounding + relevance + gate-integrity + cost
   scripts; commit the numbers to the README.
5. **API + frontend** — `/editor/briefing` + `/editor/apply`, the Editor
   panel with the approval checklist, regenerate the TS client.

## Open questions

- **Relevance gold labels**: hand-labeling per-user "should surface"
  sets is subjective. Start with one or two fixture users the author
  labels; note the small-N caveat in the README (honest limitation +
  good interview material on agent evaluation).
- **When Stories land**: does the Editor prefer Stories over raw feed
  unconditionally, or blend? Start with "prefer Stories when present,
  fall back to feed," revisit if eval shows worse picks.
- **Proposal expiry**: a briefing's `proposals` reference article ids
  that could be cleaned up before the user approves. `apply_proposals`
  must tolerate a now-missing article (skip + report), not 500.
