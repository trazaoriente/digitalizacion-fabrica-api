# Digitalizacion Fabrica API

Ejemplos de uso para los endpoints de **materials** y **batches**.

## Materials

```bash
# Crear material
curl -X POST http://localhost:8000/materials \
  -H "Content-Type: application/json" \
  -d '{"name": "Acero", "description": "Material base"}'

# Listar materiales
curl http://localhost:8000/materials

# Soft delete de un material
curl -X DELETE http://localhost:8000/materials/<material_id>
```

## Batches

```bash
# Crear batch
curl -X POST http://localhost:8000/batches \
  -H "Content-Type: application/json" \
  -d '{"material_id": "<material_id>", "batch_code": "Lote1", "quantity": 100, "production_date": "2024-01-01"}'

# Listar batches filtrando por material
curl http://localhost:8000/batches?material_id=<material_id>

# Soft delete de un batch
curl -X DELETE http://localhost:8000/batches/<batch_id>
```
