# Sample data

Tiny fixtures used to demo the API by hand or in screenshots.

- `sample_bulk_provision.json` — POST body for `/api/v1/sims/bulk_provision`.
  Each ICCID is Luhn-valid; each IMSI is 15 digits.

```bash
curl -X POST http://localhost:8000/api/v1/sims/bulk_provision \
  -H 'Content-Type: application/json' \
  -d @app/sample_data/sample_bulk_provision.json
```
