<!-- OBJETIVO (Início): Guia operacional completo do Projeto Final para o avaliador,
     descrevendo como subir toda a stack com um único comando, gerar carga e consultar os 3 sinais. -->

# Projeto Final: Observabilidade Ponta a Ponta (Métricas, Logs e Traces)

**Disciplina:** Fundamentos de Observabilidade: Métricas, Logs e Traces
**Professor:** Mateus Valgueiro
**Grupo:** Tiago Camilo (@Tiagocamilos), Danilo Huberto (@dhuberto), Eric Malone (@emcsmalone), Helierison Cardoso (@helierison), Everton Genuino (@tongenx)
**Repositório:** <https://github.com/Tiagocamilos/observabilidade>

Aplicação própria com **dois microsserviços em Python** (`loja-api` → `pagamento-service`), instrumentados com
**logs JSON**, **métricas Prometheus** e **traces OpenTelemetry** com propagação de contexto entre os serviços.
A stack de observabilidade é **Grafana + Loki + Tempo + Prometheus + Alloy**.

📄 **Documento de arquitetura e decisões:** [`docs/arquitetura-e-decisoes.md`](docs/arquitetura-e-decisoes.md)
🖼️ **Evidências (screenshots):** [`evidencias/`](evidencias/)

---

## 0. Pré-requisitos

* **Docker** com **Docker Compose v2** (`docker compose version`)
* Acesso à internet no primeiro `up`, para baixar as imagens e as dependências Python dos serviços
* Estas portas **livres no host**:

| Porta | Serviço |
| :--- | :--- |
| 3000 | Grafana |
| 3100 | Loki |
| 3200 | Tempo |
| 8080 | loja-api |
| 8081 | pagamento-service |
| 9090 | Prometheus |
| 12345 | Alloy (UI) |

> Não há `.env` nem secrets: tudo o que é necessário está versionado.

---

## 1. Como Subir Toda a Stack (Um Único Comando)

Na raiz do repositório:

```bash
docker compose up -d
```

> O `build` dos dois serviços acontece automaticamente no primeiro `up`. Se alterar o código, use
> `docker compose up -d --build`.

Verifique se os **8 serviços** estão `Up`:

```bash
docker compose ps
```

| Serviço | URL | Função |
| :--- | :--- | :--- |
| `loja-api` | <http://localhost:8080> | Microsserviço de entrada instrumentado |
| `pagamento-service` | <http://localhost:8081> | Microsserviço downstream de pagamentos |
| `trafego` | — | Gerador automático de requisições contínuas |
| `grafana` | <http://localhost:3000> | Visualização e correlação |
| `prometheus` | <http://localhost:9090> | Métricas (pull/scrape + remote write do Tempo) |
| `loki` | <http://localhost:3100> | Logs |
| `tempo` | <http://localhost:3200> | Traces (+ service graph) |
| `alloy` | <http://localhost:12345> | Coletor de logs (Docker) e traces (OTLP) |

Aguarde **~1 minuto** depois do `up` para os gráficos terem histórico.

Para derrubar tudo e apagar os dados:

```bash
docker compose down -v
```

---

## 2. Como Gerar Tráfego

1. **Automático (já ativo):** o container `trafego` executa [`trafego/gerar-trafego.sh`](trafego/gerar-trafego.sh)
   continuamente a partir do `docker compose up`, com 45% `/checkout`, 30% `/produtos`, 20% `/` e 5% `/erro`.
2. **Manual (opcional):**

   ```bash
   curl -i -X POST http://localhost:8080/checkout   # fluxo completo loja-api -> pagamento-service
   curl -i http://localhost:8080/produtos
   curl -i http://localhost:8080/erro               # erro proposital (500)
   ```

Cerca de 10% dos pagamentos falham de propósito (timeout simulado na operadora → 502), para haver erros
para observar.

---

## 3. Como Acessar o Grafana e Onde Olhar Cada Sinal

* **URL:** <http://localhost:3000>
* **Usuário:** `admin`
* **Senha:** `admin`

Os datasources **Prometheus**, **Loki** e **Tempo** e o dashboard já vêm provisionados. Não é preciso nenhuma
configuração manual.

### 3.1 Dashboard (visão unificada)

**Dashboards → Projeto Final - Observabilidade → Projeto Final - Observabilidade RED & Logs**

* **RED:** taxa por serviço e rota, % de erros 5xx, p95 global e p95 por serviço e rota
* **Exemplars:** no gráfico de p95 por rota, os losangos são exemplars. Clique em um para abrir o trace daquela requisição.
* **Negócio:** pagamentos por resultado (aprovado / recusado / inválido)
* **Service Graph:** mapa `user → loja-api → pagamento-service`, gerado pelo Tempo
* **Logs:** logs dos dois serviços, com link para o trace

### 3.2 Métricas (Prometheus)

**Explore → datasource Prometheus**

```promql
# Rate: requisições/s por serviço e rota
sum by (service, path) (rate(http_requests_total[1m]))

# Errors: fração de respostas 5xx
sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))

# Duration: latência p95 por serviço
histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket[1m])))

# Negócio: pagamentos por resultado
sum by (resultado) (rate(pagamentos_total[1m]))
```

Targets do scrape: <http://localhost:9090/targets> (4 targets `UP`).

### 3.3 Logs (Loki) → Trace

**Explore → datasource Loki**

```logql
{service=~"loja-api|pagamento-service"} | json
{service="loja-api"} | json | level="ERROR"
```

Expanda uma linha e clique no botão **Tempo** do campo `TraceID` para abrir o trace daquela requisição.

### 3.4 Traces (Tempo) → Logs

**Explore → datasource Tempo → Search → Run query**

* Abra um trace `HTTP POST /checkout`. A árvore de spans atravessa os dois serviços:
  `loja-api` (`reservar_estoque`, `chamar_pagamento_service`) → `pagamento-service` (`POST /pagar` → `analise_antifraude`).
* No span, use **Logs for this span** para ver os logs com o mesmo `trace_id`.
* Aba **Service Graph**: mapa de dependências entre os serviços.
* Para achar traces com erro (TraceQL): `{ status = error }`

---

## 4. Estrutura do Repositório

```text
.
├── compose.yaml                     # sobe app + stack com um único comando
├── services/
│   ├── loja-api/                    # app.py + Dockerfile
│   └── pagamento-service/           # app.py + Dockerfile
├── trafego/gerar-trafego.sh         # gerador de carga
├── alloy/config.alloy               # coleta de logs (Docker) e traces (OTLP)
├── loki/loki-config.yml
├── tempo/tempo.yml                  # inclui metrics-generator (service graph)
├── prometheus/prometheus.yml        # scrape dos /metrics
├── provisioning/                    # datasources + dashboard do Grafana
├── docs/arquitetura-e-decisoes.md   # documento exigido no projeto
├── evidencias/                      # screenshots + roteiro + script de verificação
└── atividade-4-misterio-checkout/   # ⚠️ Prática 4 (outra atividade, NÃO faz parte do projeto final)
```

> ⚠️ A pasta `atividade-4-misterio-checkout/` é de **outra atividade da disciplina** e tem o próprio
> `compose.yaml`, que usa as mesmas portas. O projeto final é o `compose.yaml` **da raiz**.

<!-- RESUMO FINAL (Fim): Instruções claras e reproduzíveis para execução, validação dos três
     pilares e navegação entre sinais no Grafana. -->
