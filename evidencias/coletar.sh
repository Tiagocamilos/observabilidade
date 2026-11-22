#!/bin/sh
# Coleta provas em texto de que os 3 sinais chegam ao Grafana. Rode com a stack no ar,
# ~1 min depois do "docker compose up". Saída: evidencias/saida-verificacao.txt
OUT="$(dirname "$0")/saida-verificacao.txt"
{
echo "== $(date) =="
echo; echo "## docker compose ps"; docker compose ps
echo; echo "## Prometheus: targets (esperado: 4x up)"
curl -s localhost:9090/api/v1/targets | python3 -c "import sys,json;[print(t['labels']['job'],t['health']) for t in json.load(sys.stdin)['data']['activeTargets']]"
echo; echo "## Prometheus: requisições por serviço"
curl -s 'localhost:9090/api/v1/query?query=sum%20by%20(service)%20(http_requests_total)'
echo; echo; echo "## Loki: labels service (esperado: loja-api, pagamento-service)"
curl -s localhost:3100/loki/api/v1/label/service/values
echo; echo; echo "## Loki: 1 log recente com trace_id"
curl -sG localhost:3100/loki/api/v1/query_range --data-urlencode 'query={service="loja-api"} |= "trace_id"' --data-urlencode 'limit=1'
echo; echo; echo "## Tempo: busca de traces (esperado: traces de loja-api)"
curl -s 'localhost:3200/api/search?limit=3'
echo; echo; echo "## Grafana: datasources provisionados"
curl -s -u admin:admin localhost:3000/api/datasources | python3 -c "import sys,json;[print(d['name'],d['type']) for d in json.load(sys.stdin)]"
} 2>&1 | tee "$OUT"
