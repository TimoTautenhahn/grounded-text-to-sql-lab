#!/usr/bin/env bash
# Mint a short-lived (~15 min) RDS/Aurora IAM database auth token and export it
# as PGPASSWORD, then run the Postgres publisher. No long-lived DB password is
# stored anywhere: the token is generated on demand and expires on its own.
#
# Prerequisites: AWS CLI authenticated (e.g. `aws sso login`), and the DB
# configured for IAM authentication.
#
# Usage:
#   PGHOST=your-db.cluster-xxxx.us-east-1.rds.amazonaws.com \
#   PGUSER=appuser AWS_REGION=us-east-1 \
#   ./warehouse_targets/iam_token.sh
set -euo pipefail

: "${PGHOST:?Set PGHOST to the writer endpoint}"
: "${PGUSER:?Set PGUSER to the database user}"
PGPORT="${PGPORT:-5432}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"

if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS not authenticated. Run e.g.: aws sso login" >&2
  exit 1
fi

PGPASSWORD="$(aws rds generate-db-auth-token \
  --hostname "$PGHOST" --port "$PGPORT" --username "$PGUSER" --region "$REGION")"
export PGPASSWORD PGHOST PGPORT PGUSER
export PG_SSLMODE="${PG_SSLMODE:-require}"

echo "Minted a short-lived IAM token for $PGUSER@$PGHOST (valid ~15 min)."
python "$(dirname "$0")/publish_postgres.py"
unset PGPASSWORD
