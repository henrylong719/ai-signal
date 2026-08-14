"""Prune retired source names from user_interests.preferred_sources

Revision ID: f6b7c8d9e0a1
Revises: e4f5a6b7c8d9
Create Date: 2026-08-14 10:00:00.000000

`preferred_sources` stores canonical display names from
``app.schemas.source.SOURCES``. Sources get retired from that tuple as
curation changes (dead feeds, deduplicated entries), but nothing ever
removed the retired name from rows that referenced it.

That left stale names in production rows, which broke the follow flow:
PUT /users/me/interests is a full replace, the frontend echoes back the
list it was given, and the write-path validator used to reject the whole
payload if any name was unknown — so a user who had followed a
since-retired source could not follow or unfollow *anything*. The
validator now drops unknown names instead of raising, and the read path
filters them, so the bug is fixed for live traffic either way. This
migration cleans the stored data so the rows stop carrying names that
mean nothing, and so follower counts computed off the column are honest.

The retired names are hardcoded rather than derived from SOURCES at
runtime. A migration must do the same thing whenever it runs; importing
the live tuple would make the result depend on whatever SOURCES happens
to contain at deploy time, which is exactly the coupling that produced
this bug.

Retired names are dropped, not remapped. A few look like renames
("Andrej Karpathy (YouTube)" alongside today's "Andrej Karpathy",
"Ollama Releases" alongside "Ollama Blog"), but silently moving a user's
follow onto a different feed asserts an intent they never expressed, so
we leave those as an explicit product decision rather than guessing here.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f6b7c8d9e0a1"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None

# Every name that has appeared in SOURCES and has since been removed,
# as of this revision. Derived by diffing the union of all historical
# revisions of app/schemas/source.py against the current tuple.
RETIRED_SOURCE_NAMES = (
    "3Blue1Brown",
    "AI Coffee Break",
    "Ada Lovelace Institute",
    "Analytics India Magazine",
    "Analytics Insight",
    "Andrej Karpathy (YouTube)",
    "Computerphile",
    "DeepLearningAI",
    "Every",
    "Fortune AI",
    "LangGraph Releases",
    "MIT News AI",
    "Mindstream",
    "Ollama Releases",
    "Product Hunt AI",
    "Semafor Technology",
    "Superhuman AI",
    "The Rundown AI",
    "Two Minute Papers",
    "Unite.AI",
    "Vercel AI SDK Releases",
    "Yannic Kilcher",
    "sentdex",
)


def upgrade():
    # Rebuild each affected array without the retired entries. array_agg
    # returns NULL when every element is filtered out, hence the COALESCE
    # to '{}' — the column is NOT NULL. Sorted on the way back in to match
    # the ordering crud.set_interests writes. The `&&` (overlap) guard
    # keeps this to just the rows that actually need rewriting.
    #
    # The name list is bound as a parameter rather than inlined so it is
    # written once and Postgres handles quoting.
    statement = sa.text(
        """
        UPDATE user_interests
        SET preferred_sources = COALESCE(
            (
                SELECT array_agg(name ORDER BY name)
                FROM unnest(preferred_sources) AS name
                WHERE name <> ALL (:retired)
            ),
            '{}'::text[]
        )
        WHERE preferred_sources && :retired
        """
    ).bindparams(
        sa.bindparam(
            "retired",
            value=list(RETIRED_SOURCE_NAMES),
            type_=postgresql.ARRAY(sa.Text()),
        )
    )
    op.execute(statement)


def downgrade():
    # Which user followed which retired source is not recorded anywhere
    # else, so the removed entries are unrecoverable. The column itself is
    # untouched, so this is intentionally a no-op rather than a failure —
    # same posture as c2d3e4f5a6b7.
    pass
