#! /usr/bin/env bash
set -e
set -x

if [[ -n "${TEST_POSTGRES_DB:-}" ]]; then
  export POSTGRES_DB="$TEST_POSTGRES_DB"
elif [[ "${POSTGRES_DB:-}" == test_* || "${POSTGRES_DB:-}" == *_test ]]; then
  export POSTGRES_DB="$POSTGRES_DB"
else
  export POSTGRES_DB="${POSTGRES_DB:-app}_test"
fi

python app/tests_pre_start.py

bash scripts/test.sh "$@"
