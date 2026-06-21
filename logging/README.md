# Logging — ELK + Filebeat

Stack: **Elasticsearch 8.13**, **Logstash 8.13**, **Kibana 8.13**, **Filebeat 8.13**.

## Pipeline

```
docker containers ──► filebeat (autodiscover) ──► logstash:5044
                                                     │
                                                     ▼ JSON parse, enrich
                                              elasticsearch:9200
                                                     │
                                                     ▼
                                                  kibana:5601
```

- Filebeat picks up container stdout from `/var/lib/docker/containers/*/`.
- Logstash parses JSON-encoded application logs and promotes:
  `level`, `logger`, `request_id`, `iccid`, `msisdn`, `sim_status`, `event`, `duration_ms`.
- Healthcheck noise (`/healthz`, `/readyz`) is dropped.
- Daily index pattern `sim-prov-YYYY.MM.dd`.

## Importing the Kibana dashboard

After the stack is up:

```bash
curl -X POST 'http://localhost:5601/api/saved_objects/_import?overwrite=true' \
     -H 'kbn-xsrf: true' \
     --form 'file=@logging/kibana/dashboard-sim-prov.ndjson'
```

Then open Kibana → Dashboards → **SIM Provisioning Operations**.

## Useful KQL queries

| Need                                | Query                                         |
| ----------------------------------- | --------------------------------------------- |
| All errors in last 15m              | `level:(ERROR or CRITICAL)`                   |
| Activations for one ICCIDp          | `iccid:"8991100012345678901" and event:activation` |
| Slow requests                       | `duration_ms > 1000`                          |
| API container only                  | `service:"sim-prov-api"`                      |
| Failed HLR calls                    | `event:hlr_call and app.result:failure`       |

## Production sizing notes

Single-node Elasticsearch is **dev only**. For prod, run a 3-master / 3-data
cluster on dedicated nodes with ILM (hot 7d → warm 30d → delete) and use
Filebeat → Logstash → ES instead of any direct path.
