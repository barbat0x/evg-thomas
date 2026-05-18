#!/usr/bin/env bash
# Lance scripts/postgres_init.sql avec psql (compte superutilisateur postgres).
# Usage (depuis la racine du dépôt) :
#   ./scripts/init_postgres.sh
# ou :
#   bash scripts/init_postgres.sh
#
# Si la commande échoue avec "peer authentication", essayez par exemple :
#   sudo -u postgres psql -v ON_ERROR_STOP=1 -f scripts/postgres_init.sql

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL="$ROOT/scripts/postgres_init.sql"

if [[ ! -f "$SQL" ]]; then
  echo "Fichier introuvable: $SQL" >&2
  exit 1
fi

exec psql -U postgres -v ON_ERROR_STOP=1 -f "$SQL"
