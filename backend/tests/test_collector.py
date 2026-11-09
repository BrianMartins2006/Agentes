from datetime import datetime, timezone
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("INGEST_API_KEY", "test-key")

import httpx
import pytest

from app.collector import CollectorSettings, collect_once, parse_measurement


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
