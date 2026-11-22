# Roteiro de evidências (≈10 min)

Salve cada print nesta pasta com o nome indicado (os nomes são os citados em `docs/arquitetura-e-decisoes.md`).
Suba tudo e espere ~2 min: `docker compose up -d --build`. Depois rode `./evidencias/coletar.sh`.

## Projeto Final
| # | Arquivo | Como obter |
|---|---------|-----------|
| 1 | `01-docker-compose-ps.png` | Terminal: `docker compose ps` — 8 serviços Up |
<img width="1920" height="603" alt="{C3DF1527-85A3-435D-BDCC-D6FC125FAE68}" src="https://github.com/user-attachments/assets/bd7498c1-d413-4890-851a-69e86d5d6cbd" />

| 2 | `02-grafana-dashboard-red.png` | http://localhost:3000 (admin/admin) → Dashboards → Projeto Final - Observabilidade → painel RED & Logs (mostra métricas Prometheus + logs Loki) |
| 3 | `03-loki-logs-traceid.png` | Explore → Loki → `{service=~"loja-api|pagamento-service"} \| json`; expanda uma linha e mostre o botão **Tempo** no campo TraceID |
| 4 | `04-tempo-trace-distribuido.png` | Clique no botão Tempo (ou Explore → Tempo → Search → Run query, abra um `POST /checkout`): árvore loja-api → pagamento-service |
| 5 | `05-trace-para-logs.png` | No trace, clique em **Logs for this span** (correlação trace→logs) |
| 6 | `06-prometheus-targets.png` | http://localhost:9090/targets — todos UP |

Opcional (bônus): print de um trace com erro (`/erro` ou pagamento 502) com o span em vermelho.

## Prática 4 (PDF separado)
Use a pasta `atividade-4-misterio-checkout/`. **Pare antes a stack do projeto** (`docker compose down`): as portas são as mesmas.
Para o relatório ter valor, faça o caminho do enunciado, com o `DB_POOL_SIZE=2` ORIGINAL (o compose da pasta já está corrigido; volte para 2 para reproduzir):
1. `curl` no /checkout 5x (status 500 e ~2s) — print.
2. Prometheus/Explore: erro por rota `sum by (path)(rate(http_requests_total{status=~"5.."}[1m]))/sum by (path)(rate(http_requests_total[1m]))` e p95 por rota — print mostrando só /checkout ruim.
3. Loki: `{service="loja"} | json | level="ERROR"` — print dos 3 tipos de erro (newsletter, recomendações, pool do checkout).
4. `db_conexoes_em_uso` travado no teto — print.
5. Aplique a correção (`DB_POOL_SIZE` maior), `docker compose up -d loja`, espere ~2 min e repita 1, 2 e 4 — prints "depois".
6. Anote no relatório os números REAIS que viu e os caminhos errados que tentaram.
