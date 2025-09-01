#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Detectar Python de la venv
PY="${PY:-}"
if [ -z "$PY" ]; then
  if [ -x .venv/bin/python ]; then
    PY=.venv/bin/python
  else
    PY="$(find . -maxdepth 3 -type f -path "*/.venv/bin/python" | head -n1)"
  fi
fi
if [ -z "$PY" ] || ! [ -x "$PY" ]; then
  echo "No se encontró .venv/bin/python. Corré el Setup primero." >&2
  exit 1
fi

# Entorno dev (sin Supabase ni migraciones)
export SUPABASE_ENABLED=${SUPABASE_ENABLED:-false}
export RUN_MIGRATIONS=${RUN_MIGRATIONS:-false}

# Arranque limpio
pkill -f "uvicorn app.main:app" 2>/dev/null || true
rm -f dev.db

echo ">> Levantando server…"
nohup "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info >/tmp/api.log 2>&1 &
sleep 2

echo ">> Esperando /health…"
for i in {1..15}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health || true)
  if [ "$code" = "200" ]; then echo "HEALTH=$code"; break; fi
  sleep 1
done
if [ "$code" != "200" ]; then
  echo "No arrancó. Log:"; tail -n 200 /tmp/api.log || true; exit 1
fi

echo ">> /docs"; curl -s -o /dev/null -w "DOCS=%{http_code}\n" http://127.0.0.1:8000/docs

# Crear material
NAME=${NAME:-"Envase PET 500"}
DESC=${DESC:-"botella 500 ml"}
echo ">> Creando material: $NAME"
curl -s -X POST http://127.0.0.1:8000/materials/ \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$NAME\",\"description\":\"$DESC\"}" > /tmp/material.json
echo "Material:"; cat /tmp/material.json; echo

MID=$("$PY" - <<'PY'
import json
try:
    print(json.load(open("/tmp/material.json")).get("id",""))
except Exception:
    print("")
PY
)
[ -n "$MID" ] || { echo "No se obtuvo id de material"; tail -n 200 /tmp/api.log || true; exit 1; }
echo "MID=$MID"

# Crear batch
BATCH=${BATCH:-"L-0001"}
QTY=${QTY:-1000}
DATE=${DATE:-"2025-08-31"}
echo ">> Creando batch: $BATCH"
curl -s -X POST http://127.0.0.1:8000/batches/ \
  -H "Content-Type: application/json" \
  -d "{\"material_id\":\"$MID\",\"batch_code\":\"$BATCH\",\"quantity\":$QTY,\"production_date\":\"$DATE\"}" > /tmp/batch.json
echo "Batch:"; cat /tmp/batch.json; echo

echo ">> Listando batches del material"
curl -s "http://127.0.0.1:8000/batches/?material_id=$MID"; echo

echo "Listo ✅  (para parar: pkill -f 'uvicorn app.main:app')"
