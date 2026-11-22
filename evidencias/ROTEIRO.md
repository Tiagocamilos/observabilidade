# Roteiro de evidências (≈10 min)

Salve cada print **nesta pasta** com o nome indicado: são os nomes citados em `docs/arquitetura-e-decisoes.md`
(seção 7). Os prints ficam como **arquivos PNG commitados** (não só anexos colados no GitHub), para não se
perderem numa entrega em ZIP.

1. Suba tudo: `docker compose up -d --build` e espere ~2 min.
2. Rode `./evidencias/coletar.sh` (atualiza `saida-verificacao.txt` com provas em texto).
3. Tire os prints abaixo.

## Projeto Final

| # | Arquivo | O que mostra / como obter |
|---|---------|---------------------------|
| 1 | [`01-docker-compose-ps.png`](01-docker-compose-ps.png) | Terminal: `docker compose ps`, com os 8 serviços `Up` |
| 2 | [`02-grafana-dashboard-red.png`](02-grafana-dashboard-red.png) | <http://localhost:3000> (admin/admin) → Dashboards → Projeto Final - Observabilidade → RED & Logs (**métricas** Prometheus + logs Loki) |
| 3 | [`03-loki-logs-traceid.png`](03-loki-logs-traceid.png) | Explore → Loki → `{service=~"loja-api\|pagamento-service"} \| json`; linha expandida com o botão **Tempo** no campo TraceID (**logs**) |
| 4 | [`04-tempo-trace-distribuido.png`](04-tempo-trace-distribuido.png) | Explore → Tempo → `HTTP POST /checkout`: spans `loja-api` → `pagamento-service` (**traces** + context propagation) |
| 5 | [`05-trace-para-logs.png`](05-trace-para-logs.png) | No trace, **Logs for this span**: correlação trace → logs (`pagamento-service`) |
| 5b | [`05b-trace-para-logs-loja-api.png`](05b-trace-para-logs-loja-api.png) | Mesma correlação, para um span da `loja-api` (filtro `trace_id=...`) |
| 6 | [`06-prometheus-targets.png`](06-prometheus-targets.png) | <http://localhost:9090/targets>, com todos os targets `UP` |
| 7 | [`07-loki-log-erro.png`](07-loki-log-erro.png) | Loki: `{service=~"loja-api\|pagamento-service"} \| json \| level="ERROR"` (logs de erro com `trace_id`) |
| 8 | [`08b-tempo-trace-erro-checkout.png`](08b-tempo-trace-erro-checkout.png) | Tempo: trace de `POST /checkout` com 502 do pagamento (span em vermelho) |
| 9 | [`09-prometheus-erros.png`](09-prometheus-erros.png) | Prometheus: `sum by (service, path) (rate(http_requests_total{status=~"5.."}[1m]))` |
| 10 | `10-service-graph.png` | ❌ **falta** (depende das mudanças da branch `polimento`). Explore → Tempo → aba **Service Graph** (ou o painel no dashboard): `user → loja-api → pagamento-service` |

Opcional: print do painel de p95 com os **exemplars** (losangos) e o trace aberto ao clicar em um deles.

## Prática 4 (PDF separado no diretório: atividade-4-misterio-checkout/ )
No diretório `atividade-4-misterio-checkout/`. **Pare antes a stack do projeto** (`docker compose down`): as portas são as mesmas.
Para o relatório ter valor, faça o caminho do enunciado, com o `DB_POOL_SIZE=2` ORIGINAL (o compose da pasta já está corrigido; volte para 2 para reproduzir):
1. `curl` no /checkout 5x (status 500 e ~2s) — print.
2. Prometheus/Explore: erro por rota `sum by (path)(rate(http_requests_total{status=~"5.."}[1m]))/sum by (path)(rate(http_requests_total[1m]))` e p95 por rota — print mostrando só /checkout ruim.
3. Loki: `{service="loja"} | json | level="ERROR"` — print dos 3 tipos de erro (newsletter, recomendações, pool do checkout).
4. `db_conexoes_em_uso` travado no teto — print.
5. Aplique a correção (`DB_POOL_SIZE` maior), `docker compose up -d loja`, espere ~2 min e repita 1, 2 e 4 — prints "depois".
6. Anote no relatório os números REAIS que viu e os caminhos errados que tentaram.
