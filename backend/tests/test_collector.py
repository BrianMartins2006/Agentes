from datetime import datetime, timezone
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("INGEST_API_KEY", "test-key")

import httpx
import pytest

from app.collector import CollectorSettings, collect_once, parse_measurement, describe_failure, create_esp32_client


# HTML shape from the supplied firmware; synthetic readings, no Wi-Fi credentials.
HTML = """<html><body><h1>Monitoramento ESP32</h1>
<div class='card'><h2>Temperatura</h2>25.0 C</div>
<div class='card'><h2>Umidade do ar</h2>65.0 %</div>
<div class='card'><h2>Umidade do solo</h2>50 %
<p>Leitura: 3498</p><p>Solo umido</p></div></body></html>"""
NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def test_parse_firmware_page():
    measurement = parse_measurement(HTML, "esp32-01", NOW)
    assert measurement.temperature_c == 25
    assert measurement.air_humidity_pct == 65
    assert measurement.soil_raw == 3498
    assert measurement.measured_at == NOW


@pytest.mark.parametrize("html", [
    HTML.replace("25.0 C", "Erro no sensor"),
    HTML.replace("65.0 %", "Erro no sensor"),
    HTML.replace("65.0 %", "101.0 %"),
    HTML.replace("Leitura: 3498", "Leitura: NaN"),
    HTML + "<div class='card'><h2>Temperatura</h2>26.0 C</div>",
    "<html>Página indisponível</html>",
])
def test_reject_bad_samples(html):
    with pytest.raises(ValueError):
        parse_measurement(html, "esp32-01", NOW)


def test_collect_and_send_without_leaking_key():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.host == "esp32.local":
            assert "x-api-key" not in request.headers
            return httpx.Response(200, text=HTML)
        assert request.method == "POST"
        assert request.url.path == "/api/v1/measurements"
        assert request.headers["x-api-key"] == "collector-secret"
        import json
        body = json.loads(request.content)
        assert body["soil_raw"] == 3498
        assert body["measured_at"].endswith("Z")
        return httpx.Response(201, json={"id": 12})

    config = CollectorSettings(esp32_url="http://esp32.local/", ingest_api_key="collector-secret")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert collect_once(client, config) == 12
    assert len(requests) == 2


def test_sensor_failure_does_not_send_sample():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, text=HTML.replace("25.0 C", "Erro no sensor"))

    config = CollectorSettings(esp32_url="http://esp32.local/")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            collect_once(client, config)
    assert len(requests) == 1


def test_backend_timeout_does_not_retry():
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, text=HTML)
        raise httpx.ReadTimeout("timeout", request=request)

    config = CollectorSettings(esp32_url="http://esp32.local/")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ReadTimeout):
            collect_once(client, config)
    assert len(requests) == 2


@pytest.mark.parametrize("method,stage", [("GET", "ESP32"), ("POST", "API")])
def test_connection_error_identifies_stage_without_credentials(method, stage):
    request = httpx.Request(method, "https://user:secret@example.com/?key=private")
    error = httpx.ConnectError("sensitive detail", request=request)
    description = describe_failure(error)
    assert stage in description
    assert "ConnectError" in description
    assert "secret" not in description
    assert "private" not in description
    assert "sensitive" not in description


def test_local_collection_bypasses_environment_proxy(monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.headers['Connection'] == 'close'
            assert 'X-API-Key' not in self.headers
            body = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    for variable in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
        monkeypatch.setenv(variable, 'http://127.0.0.1:1')
    monkeypatch.setenv('NO_PROXY', '')
    monkeypatch.setenv('no_proxy', '')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    config = CollectorSettings(esp32_url=f'http://127.0.0.1:{server.server_port}/')
    def api_handler(request):
        assert request.method == 'POST'
        return httpx.Response(201, json={'id': 99})
    try:
        with create_esp32_client(config) as local, httpx.Client(transport=httpx.MockTransport(api_handler)) as api:
            assert collect_once(api, config, esp32_client=local) == 99
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
