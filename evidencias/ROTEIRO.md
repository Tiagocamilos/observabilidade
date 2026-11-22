# Roteiro de evidências (≈10 min)

Salve cada print **nesta pasta**, com o nome indicado. Esses são os nomes citados em
`docs/arquitetura-e-decisoes.md`, seção 7. Os prints precisam estar como **arquivos PNG commitados**, não só
como anexos colados no GitHub, porque numa entrega em ZIP os anexos se perdem.

1. Suba tudo: `docker compose up -d --build` e espere ~2 min.
2. Rode `./evidencias/coletar.sh`. Ele atualiza `saida-verificacao.txt` com provas em texto.
3. Tire os prints abaixo.

## Projeto Final

| # | Arquivo | Status | Como obter |
|---|---------|--------|-----------|
| 1 | [`01-docker-compose-ps.png`](01-docker-compose-ps.png) | ✅ (refazer: a lista de portas do Alloy mudou) | Terminal: `docker compose ps` com os 8 serviços `Up` |
| 2 | [`02-grafana-dashboard-red.png`](02-grafana-dashboard-red.png) | ✅ (refazer: o painel ganhou Service Graph e Pagamentos) | <http://localhost:3000> (admin/admin) → Dashboards → Projeto Final - Observabilidade → RED & Logs |
| 3 | `03-loki-logs-traceid.png` | ❌ falta | Explore → Loki → `{service=~"loja-api\|pagamento-service"} \| json`; expanda uma linha e mostre o botão **Tempo** no campo TraceID |
| 4 | `04-tempo-trace-distribuido.png` | ❌ falta | Clique no botão Tempo (ou Explore → Tempo → Search → Run query) e abra um `HTTP POST /checkout` com os spans `loja-api` → `pagamento-service` expandidos |
| 5 | `05-trace-para-logs.png` | ❌ falta | No trace, clique em **Logs for this span** (correlação trace → logs) |
| 6 | `06-prometheus-targets.png` | ❌ falta | <http://localhost:9090/targets>, com os 4 targets `UP` |
| 7 | `07-service-graph.png` | ❌ falta | Explore → Tempo → aba **Service Graph** (ou o painel no dashboard), mostrando `loja-api → pagamento-service` |
| 8 | `08-trace-com-erro.png` | ❌ falta | Explore → Tempo → TraceQL `{ status = error }` → abra um `POST /checkout` com 502 do pagamento (span vermelho + exceção) |

Opcional: print do painel de p95 com os **exemplars** (losangos) e do trace aberto ao clicar num deles.

## Prática 4 (PDF separado)
Use a pasta `atividade-4-misterio-checkout/`. **Pare antes a stack do projeto** (`docker compose down`): as portas são as mesmas.
Para o relatório ter valor, faça o caminho do enunciado, com o `DB_POOL_SIZE=2` ORIGINAL (o compose da pasta já está corrigido; volte para 2 para reproduzir):
1. `curl` no /checkout 5x (status 500 e ~2s) — print.
2. Prometheus/Explore: erro por rota `sum by (path)(rate(http_requests_total{status=~"5.."}[1m]))/sum by (path)(rate(http_requests_total[1m]))` e p95 por rota — print mostrando só /checkout ruim.
3. Loki: `{service="loja"} | json | level="ERROR"` — print dos 3 tipos de erro (newsletter, recomendações, pool do checkout).
4. `db_conexoes_em_uso` travado no teto — print.
5. Aplique a correção (`DB_POOL_SIZE` maior), `docker compose up -d loja`, espere ~2 min e repita 1, 2 e 4 — prints "depois".
6. Anote no relatório os números REAIS que viu e os caminhos errados que tentaram.
