# Evidências de execução

Prints tirados com a stack no ar (`docker compose up -d --build`). 
Conteúdo em texto: [`saida-verificacao.txt`](saida-verificacao.txt) (gerado pela execução do `coletar.sh`).

## 1. Stack no ar
![docker compose ps](01-docker-compose-ps.png)

## 2. Métricas (Prometheus → Grafana)
Targets do Prometheus:
![targets](06-prometheus-targets.png)

Dashboard RED provisionado:
![dashboard RED](02-grafana-dashboard-red.png)

Respostas 5xx por serviço e rota:
![erros 5xx](09-prometheus-erros.png)

## 3. Logs (Alloy → Loki → Grafana)
Logs JSON com `trace_id` e link para o Tempo:
![logs com trace_id](03-loki-logs-traceid.png)

Logs de erro (`level="ERROR"`):
![logs de erro](07-loki-log-erro.png)

## 4. Traces (OpenTelemetry → Alloy → Tempo → Grafana)
Trace distribuído `POST /checkout` (loja-api → pagamento-service):
![trace distribuído](04-tempo-trace-distribuido.png)

Trace de checkout com erro (atravessa os dois serviços):
![trace com erro](08b-tempo-trace-erro-checkout.png)

## 5. Correlação trace → logs
Logs do `pagamento-service` filtrados pelo `trace_id` do trace:
![trace para logs](05-trace-para-logs.png)

Logs da `loja-api` filtrados pelo mesmo mecanismo:
![trace para logs loja-api](05b-trace-para-logs-loja-api.png)
