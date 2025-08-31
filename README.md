# Digitalizacion Fabrica API

Ejemplos de uso para los nuevos endpoints `materials` y `batches`.

## Materials
```bash
# Crear material
curl -X POST http://localhost:8000/materials/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Steel","description":"Acero"}'

# Listar materiales activos
curl http://localhost:8000/materials/

# Soft delete de un material
curl -X DELETE http://localhost:8000/materials/<material_id>
```

## Batches
```bash
# Crear batch
curl -X POST http://localhost:8000/batches/ \
  -H "Content-Type: application/json" \
  -d '{"material_id":"<material_id>","batch_code":"B001","quantity":10,"production_date":"2024-01-01"}'

# Listar batches por material
curl "http://localhost:8000/batches?material_id=<material_id>"

# Soft delete de un batch
curl -X DELETE http://localhost:8000/batches/<batch_id>
```

## Fallback de DB (sandbox)

- En desarrollo/sandbox (SQLite) el servicio crea tablas automáticamente al arrancar.
- En producción se recomienda usar Alembic; el fallback es idempotente y seguro en ambos casos.
