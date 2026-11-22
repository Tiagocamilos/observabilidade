# OBJETIVO (Início): Implementar o microsserviço de entrada 'loja-api' instrumentado com os
# três pilares da observabilidade: Logs JSON com trace_id, Métricas RED/Gauge e Traces OTel
# com spans manuais e propagação de contexto W3C (traceparent) para o 'pagamento-service'.

import json
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, REGISTRY, generate_latest
from prometheus_client.openmetrics.exposition import (
    CONTENT_TYPE_LATEST as OPENMETRICS_CONTENT_TYPE,
    generate_latest as generate_openmetrics,
)

SERVICE_NAME = os.environ.get("SERVICE_NAME", "loja-api")
PORT = int(os.environ.get("PORT", "8080"))
PAGAMENTO_URL = os.environ.get("PAGAMENTO_URL", "http://pagamento-service:8081")
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://alloy:4318/v1/traces")

resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

REQUESTS = Counter(
    "http_requests_total",
    "Total de requisições HTTP atendidas",
    ["service", "path", "status"],
)

DURATION = Histogram(
    "http_request_duration_seconds",
    "Duração das requisições HTTP em segundos",
    ["service", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

IN_PROGRESS = Gauge(
    "pedidos_em_andamento",
    "Número de requisições em processamento simultâneo",
    ["service"],
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


KNOWN_PATHS = {"/", "/produtos", "/checkout", "/erro"}


class LojaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def _handle_request(self):
        if self.path == "/metrics":
            self._send_metrics()
            return

        route = self.path if self.path in KNOWN_PATHS else "outro"
        request_id = str(uuid4())
        start = time.time()
        IN_PROGRESS.labels(service=SERVICE_NAME).inc()

        with tracer.start_as_current_span(
            f"HTTP {self.command} {route}", kind=SpanKind.SERVER
        ) as root_span:
            root_span.set_attribute("http.request.method", self.command)
            root_span.set_attribute("http.route", route)
            root_span.set_attribute("request.id", request_id)

            try:
                if route == "/checkout":
                    status, payload = self._processar_checkout(root_span, request_id)
                elif route == "/produtos":
                    time.sleep(random.uniform(0.02, 0.09))
                    status, payload = 200, {"produtos": ["Notebook", "Monitor", "Teclado"]}
                elif route == "/erro":
                    raise RuntimeError("Falha simulada na camada de negócio da loja-api")
                else:
                    time.sleep(random.uniform(0.005, 0.03))
                    status, payload = 200, {"status": "loja online"}

            except Exception as exc:
                status = 500
                payload = {"erro": str(exc)}
                root_span.record_exception(exc)
                root_span.set_status(Status(StatusCode.ERROR, str(exc)))

            finally:
                duration = time.time() - start
                duration_ms = round(duration * 1000, 2)
                IN_PROGRESS.labels(service=SERVICE_NAME).dec()

                root_span.set_attribute("http.response.status_code", status)
                REQUESTS.labels(service=SERVICE_NAME, path=route, status=str(status)).inc(
                    exemplar=exemplar()
                )
                DURATION.labels(service=SERVICE_NAME, path=route).observe(
                    duration, exemplar=exemplar()
                )

                if status >= 500:
                    log(
                        "ERROR",
                        "Falha ao processar requisição na loja-api",
                        request_id=request_id,
                        path=route,
                        status=status,
                        duration_ms=duration_ms,
                        erro=payload.get("erro", ""),
                    )
                else:
                    log(
                        "INFO",
                        "Requisição atendida com sucesso na loja-api",
                        request_id=request_id,
                        path=route,
                        status=status,
                        duration_ms=duration_ms,
                    )

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

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

    def _processar_checkout(self, parent_span, request_id: str):
        pedido_id = f"PED-{random.randint(1000, 9999)}"
        valor = round(random.uniform(50.0, 1200.0), 2)
        parent_span.set_attribute("pedido.id", pedido_id)
        parent_span.set_attribute("pedido.valor", valor)

        with tracer.start_as_current_span("reservar_estoque") as estoque_span:
            estoque_span.set_attribute("pedido.id", pedido_id)
            estoque_span.add_event("verificando_disponibilidade_sku")
            time.sleep(random.uniform(0.03, 0.12))
            estoque_span.add_event("estoque_reservado_com_sucesso")

        with tracer.start_as_current_span(
            "chamar_pagamento_service", kind=SpanKind.CLIENT
        ) as call_span:
            call_span.set_attribute("http.request.method", "POST")
            call_span.set_attribute("server.address", PAGAMENTO_URL)
            headers = {"Content-Type": "application/json"}
            TraceContextTextMapPropagator().inject(headers)

            body = json.dumps({"pedido_id": pedido_id, "valor": valor}).encode("utf-8")
            req = urllib.request.Request(
                f"{PAGAMENTO_URL}/pagar", data=body, headers=headers, method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    resp_body = json.loads(resp.read().decode("utf-8"))
                    call_span.set_attribute("http.response.status_code", resp.status)
                    call_span.set_attribute("pagamento.status", "aprovado")
                    call_span.add_event("pagamento_aprovado")
                    return 200, {"pedido_id": pedido_id, "pagamento": resp_body}
            except urllib.error.HTTPError as http_err:
                call_span.set_attribute("http.response.status_code", http_err.code)
                call_span.set_attribute("pagamento.status", "recusado")
                call_span.set_status(Status(StatusCode.ERROR, f"HTTP {http_err.code}"))
                raise RuntimeError(
                    f"Pagamento recusado pelo serviço downstream (HTTP {http_err.code})"
                ) from http_err
            except (urllib.error.URLError, TimeoutError) as conn_err:
                # Falha de rede/timeout: o downstream nem respondeu.
                call_span.record_exception(conn_err)
                call_span.set_attribute("pagamento.status", "indisponivel")
                call_span.set_status(Status(StatusCode.ERROR, "pagamento-service indisponível"))
                raise RuntimeError(
                    f"pagamento-service indisponível: {conn_err}"
                ) from conn_err

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    log("INFO", f"Iniciando {SERVICE_NAME} na porta {PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), LojaHandler).serve_forever()

# RESUMO FINAL (Fim): Fornece o serviço de entrada instrumentado com métricas RED, logs JSON
# correlacionados por trace_id, spans manuais e propagação distribuída W3C para o pagamento-service.
