"""Read the existing ESP32 HTML page without modifying its firmware."""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import logging
import re
import time

import httpx
from pydantic import Field, HttpUrl, ValidationError

from app.config import Settings
from app.schemas import MeasurementCreate

logger = logging.getLogger(__name__)


class CollectorSettings(Settings):
    esp32_url: HttpUrl
    device_id: str = "esp32-01"
    api_base_url: HttpUrl = HttpUrl("http://127.0.0.1:8000")
    poll_seconds: float = Field(default=10, ge=3, allow_inf_nan=False)


class CardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards: list[str] = []
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif "card" in dict(attrs).get("class", "").split():
                self.depth = 1
                self.parts = []

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "div" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.cards.append(" ".join(part for part in self.parts if part))


def parse_measurement(html: str, device_id: str, measured_at: datetime) -> MeasurementCreate:
    parser = CardParser()
    parser.feed(html)
    values = {}
    patterns = {
        "temperature_c": r"Temperatura\s+(-?\d+(?:\.\d+)?)\s+C",
        "air_humidity_pct": r"Umidade do ar\s+(\d+(?:\.\d+)?)\s+%",
        "soil_raw": r"Umidade do solo\s+\d+\s+%\s+Leitura:\s+(\d+)(?:\s+.*)?",
    }
    for field, pattern in patterns.items():
        matches = [re.fullmatch(pattern, card) for card in parser.cards]
        matches = [match for match in matches if match is not None]
        if len(matches) != 1:
            raise ValueError(f"Leitura ausente, inválida ou duplicada: {field}")
        value = matches[0].group(1)
        values[field] = int(value) if field == "soil_raw" else float(value)
    return MeasurementCreate(device_id=device_id, measured_at=measured_at, **values)


def collect_once(client: httpx.Client, config: CollectorSettings) -> int:
    # The API key is sent only to the backend, never to the ESP32.
    response = client.get(str(config.esp32_url))
    response.raise_for_status()
    payload = parse_measurement(response.text, config.device_id, datetime.now(timezone.utc))
    result = client.post(
        str(config.api_base_url).rstrip("/") + "/api/v1/measurements",
        headers={"X-API-Key": config.ingest_api_key.get_secret_value()},
        json=payload.model_dump(mode="json"),
    )
    result.raise_for_status()
    return result.json()["id"]


def main():
    args_parser = argparse.ArgumentParser(description=__doc__)
    args_parser.add_argument("--once", action="store_true", help="Coletar apenas uma amostra")
    args = args_parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = CollectorSettings()
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            while True:
                try:
                    identifier = collect_once(client, config)
                    logger.info("Medição armazenada: id=%s", identifier)
                except (httpx.HTTPError, ValueError, KeyError, ValidationError) as exc:
                    # Do not log HTML, credentials or server response bodies.
                    logger.error("Coleta não concluída (%s). Verifique rede, sensores e configuração.",
                                 type(exc).__name__)
                    if args.once:
                        raise SystemExit(1) from None
                if args.once:
                    break
                # No automatic resending: a timeout on POST may occur after persistence.
                time.sleep(config.poll_seconds)
    except KeyboardInterrupt:
        logger.info("Coletor encerrado")


if __name__ == "__main__":
    main()
