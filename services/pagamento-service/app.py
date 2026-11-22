# OBJETIVO (Início): Implementar o microsserviço 'pagamento-service' que extrai o contexto W3C
# (traceparent) enviado pela 'loja-api', cria spans filhos no mesmo trace distribuído, emite logs
# estruturados com o mesmo trace_id e expõe métricas RED próprias em /metrics.

import json
import os
import random
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, REGISTRY, generate_latest
from prometheus_client.openmetrics.exposition import (
    CONTENT_TYPE_LATEST as OPENMETRICS_CONTENT_TYPE,
    generate_latest as generate_openmetrics,
)

SERVICE_NAME = os.environ.get("SERVICE_NAME", "pagamento-service")
PORT = int(os.environ.get("PORT", "8081"))
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy:4318/v1/traces")
# Probabilidade de falha simulada na operadora de cartão (padrão: 10%)
TAXA_FALHA = float(os.environ.get("TAXA_FALHA_PAGAMENTO", "0.10"))

resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

REQUESTS = Counter(
    "http_requests_total",
    "Total de requisições HTTP no serviço de pagamento",
    ["service", "path", "status"],
)

DURATION = Histogram(
    "http_request_duration_seconds",
    "Latência de processamento de pagamentos em segundos",
    ["service", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

PAGAMENTOS = Counter(
    "pagamentos_total",
    "Pagamentos processados por resultado (aprovado, recusado, invalido)",
    ["service", "resultado"],
)


def current_ids():
    """Retorna (trace_id, span_id) do span ativo em hexadecimal, ou strings vazias."""
    span_ctx = trace.get_current_span().get_span_context()
    if not span_ctx.is_valid:
        return "", ""
    return format(span_ctx.trace_id, "032x"), format(span_ctx.span_id, "016x")


def exemplar():
    """Exemplar com o trace_id atual: permite pular de um ponto do gráfico para o trace."""
    trace_id, _ = current_ids()
    return {"trace_id": trace_id} if trace_id else None


def log(level: str, message: str, **extra) -> None:
    trace_id, span_id = current_ids()

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": SERVICE_NAME,
        "message": message,
        "trace_id": trace_id,
        "span_id": span_id,
    }
    record.update(extra)
    print(json.dumps(record, ensure_ascii=False), flush=True)


class PagamentoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self._send_metrics()
            return

        self._send_json(200, {"status": "pagamento-service ativo"})

    def do_POST(self):
        if self.path != "/pagar":
            self._send_json(404, {"erro": "rota não encontrada"})
            return

        start = time.time()
        carrier = {k.lower(): v for k, v in self.headers.items()}
        parent_context = TraceContextTextMapPropagator().extract(carrier=carrier)

        # SpanKind.SERVER + o CLIENT da loja-api formam a aresta loja-api -> pagamento-service
        # no Service Graph gerado pelo Tempo.
        with tracer.start_as_current_span(
            "POST /pagar", context=parent_context, kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("http.request.method", "POST")
            span.set_attribute("http.route", "/pagar")

            try:
                content_len = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                dados = json.loads(raw_body)
            except (ValueError, UnicodeDecodeError) as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, "corpo da requisição inválido"))
                self._finalizar(span, start, 400, {"erro": "corpo inválido"}, "invalido",
                                "WARN", "Requisição de pagamento com corpo inválido",
                                detalhe=str(exc))
                return

            pedido_id = dados.get("pedido_id", "desconhecido")
            valor = dados.get("valor", 0.0)
            span.set_attribute("pedido.id", pedido_id)
            span.set_attribute("pedido.valor", valor)

            with tracer.start_as_current_span("analise_antifraude") as fraude_span:
                fraude_span.add_event("consultando_score_risco")
                time.sleep(random.uniform(0.05, 0.35))
                score = round(random.uniform(0, 1), 3)
                fraude_span.set_attribute("antifraude.score", score)
                fraude_span.add_event("score_calculado", {"antifraude.score": score})

                if random.random() < TAXA_FALHA:
                    err_msg = "Timeout na comunicação com operadora de cartão"
                    exc = TimeoutError(err_msg)
                    fraude_span.record_exception(exc)
                    fraude_span.set_status(Status(StatusCode.ERROR, err_msg))
                    span.set_status(Status(StatusCode.ERROR, err_msg))
                    self._finalizar(span, start, 502, {"erro": err_msg}, "recusado",
                                    "ERROR", err_msg, pedido_id=pedido_id, valor=valor)
                    return

            self._finalizar(span, start, 200, {"status": "aprovado", "pedido_id": pedido_id},
                            "aprovado", "INFO", "Pagamento aprovado com sucesso",
                            pedido_id=pedido_id, valor=valor)

    def _finalizar(self, span, start, status, payload, resultado, level, message, **extra):
        """Ponto único de saída: métricas (com exemplar), log correlacionado e resposta."""
        duration = time.time() - start
        span.set_attribute("http.response.status_code", status)
        REQUESTS.labels(service=SERVICE_NAME, path="/pagar", status=str(status)).inc(
            exemplar=exemplar()
        )
        DURATION.labels(service=SERVICE_NAME, path="/pagar").observe(
            duration, exemplar=exemplar()
        )
        PAGAMENTOS.labels(service=SERVICE_NAME, resultado=resultado).inc()
        log(level, message, path="/pagar", status=status,
            duration_ms=round(duration * 1000, 2), **extra)
        self._send_json(status, payload)

    def _send_metrics(self):
        # Prometheus pede OpenMetrics no header Accept: só nesse formato os exemplars são expostos.
        if "application/openmetrics-text" in self.headers.get("Accept", ""):
            content_type, body = OPENMETRICS_CONTENT_TYPE, generate_openmetrics(REGISTRY)
        else:
            content_type, body = CONTENT_TYPE_LATEST, generate_latest()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    log("INFO", f"Iniciando {SERVICE_NAME} na porta {PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), PagamentoHandler).serve_forever()

# RESUMO FINAL (Fim): Completa o rastreamento distribuído ponta a ponta ao continuar o trace_id
# originado na loja-api, permitindo visualizar no Grafana Tempo toda a jornada da transação.
