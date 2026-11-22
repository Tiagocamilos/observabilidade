# Roteiro de evidências (≈10 min)

Salve cada print nesta pasta com o nome indicado (os nomes são os citados em `docs/arquitetura-e-decisoes.md`).
Suba tudo e espere ~2 min: `docker compose up -d --build`. Depois rode `./evidencias/coletar.sh`.

## Projeto Final
| # | Arquivo | Como obter |
|---|---------|-----------|
| 1 | `01-docker-compose-ps.png` | Terminal: `docker compose ps` — 8 serviços Up |
<img width="1920" height="603" alt="{C3DF1527-85A3-435D-BDCC-D6FC125FAE68}" src="https://github.com/user-attachments/assets/bd7498c1-d413-4890-851a-69e86d5d6cbd" />

| 2 | `02-grafana-dashboard-red.png` | http://localhost:3000 (admin/admin) → Dashboards → Projeto Final - Observabilidade → painel RED & Logs (mostra métricas Prometheus + logs Loki) |
<img width="1359" height="744" alt="{8BF8951B-B2CD-4DB8-AA3A-CB124EB139B9}" src="https://github.com/user-attachments/assets/005a5afa-7b4e-4f61-ad12-89d454fa6f34" />

| 3 | `03-loki-logs-traceid.png` | Explore → Loki → `{service=~"loja-api|pagamento-service"} \| json`; expanda uma linha e mostre o botão **Tempo** no campo TraceID |
<img width="1124" height="659" alt="{2046E850-C14F-4558-860F-5FFA0870B6B5}" src="https://github.com/user-attachments/assets/80aa52d1-aaf3-4697-842e-4de043ca5629" />


| 4 | `04-tempo-trace-distribuido.png` | Clique no botão Tempo (ou Explore → Tempo → Search → Run query, abra um `POST /checkout`): árvore loja-api → pagamento-service | <img width="972" height="665" alt="{9FDC3BE9-8701-40AB-B836-9C863E8A5B54}" src="https://github.com/user-attachments/assets/4d17e9a2-30d3-4243-b3ef-fac3d805d650" />


| 5 | `05-trace-para-logs.png` | No trace, clique em **Logs for this span** (correlação trace→logs) |
<img width="797" height="664" alt="{B6DBEC7B-5C13-442E-9FE4-0AD8AE4EE733}" src="https://github.com/user-attachments/assets/06961fb7-5cc6-41d2-900c-24bf8b02b0a6" />
<img width="845" height="668" alt="{9A7F6ABC-A03B-40BC-BFBE-A67969C795FA}" src="https://github.com/user-attachments/assets/d9b7dee5-2480-461a-8221-8af844fecda0" />

| 6 | `06-prometheus-targets.png` | http://localhost:9090/targets — todos UP |
<img width="1304" height="664" alt="{6102226C-EB81-41B5-8EFC-EA71B11FBEA0}" src="https://github.com/user-attachments/assets/23de9061-557f-487a-b25c-991bdef3a4d4" />

| 7 | Print de um trace com erro (`/erro` ou pagamento 502) com o span em vermelho.
<img width="1277" height="644" alt="{3367C954-5BFA-41C9-A4B3-FE3BC6D1AE75}" src="https://github.com/user-attachments/assets/0872647b-fc8a-4ead-8d50-4f196dcd2f1a" />
<img width="1203" height="664" alt="{FFD829C4-B153-45A5-862C-EA0A18DC567C}" src="https://github.com/user-attachments/assets/7c0b748a-ce30-443b-803a-827a19a7d6fd" />

| 8 |

| 9 | 09-prometheus-erros.png
<img width="1290" height="652" alt="{58766DAE-2ED0-4F93-A331-EC0E6BD69F6D}" src="https://github.com/user-attachments/assets/976ea34c-bea5-4218-a89a-8ae97485c668" />



## Prática 4 (PDF separado no diretório: atividade-4-misterio-checkout/ )
No diretório `atividade-4-misterio-checkout/`. **Pare antes a stack do projeto** (`docker compose down`): as portas são as mesmas.
Para o relatório ter valor, faça o caminho do enunciado, com o `DB_POOL_SIZE=2` ORIGINAL (o compose da pasta já está corrigido; volte para 2 para reproduzir):
1. `curl` no /checkout 5x (status 500 e ~2s) — print.
2. Prometheus/Explore: erro por rota `sum by (path)(rate(http_requests_total{status=~"5.."}[1m]))/sum by (path)(rate(http_requests_total[1m]))` e p95 por rota — print mostrando só /checkout ruim.
3. Loki: `{service="loja"} | json | level="ERROR"` — print dos 3 tipos de erro (newsletter, recomendações, pool do checkout).
4. `db_conexoes_em_uso` travado no teto — print.
5. Aplique a correção (`DB_POOL_SIZE` maior), `docker compose up -d loja`, espere ~2 min e repita 1, 2 e 4 — prints "depois".
6. Anote no relatório os números REAIS que viu e os caminhos errados que tentaram.
