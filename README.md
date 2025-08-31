# Digitalizacion Fabrica API

## Materials
```bash
curl -X POST http://localhost:8000/materials \
     -H 'Content-Type: application/json' \
     -d '{"name": "Acero", "description": "metal"}'

curl 'http://localhost:8000/materials?search=ac'
```

## Batches
```bash
curl -X POST http://localhost:8000/batches \
     -H 'Content-Type: application/json' \
     -d '{"material_id": "<MATERIAL_ID>", "batch_code": "L001", "quantity": 10, "production_date": "2024-01-01"}'

curl 'http://localhost:8000/batches?material_id=<MATERIAL_ID>'
```
