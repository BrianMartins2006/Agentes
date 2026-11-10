#include <WiFi.h>
#include <WebServer.h>
#include <WiFiManager.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <NetworkClientSecure.h>
#include <time.h>
#include "secrets.h"

#define DHTPIN 4
#define DHTTYPE DHT11
#define SENSOR_SOLO 34
#define SOLO_SECO 4095
#define SOLO_MOLHADO 2901

// Senha da rede de configuracao da placa, nao da rede Wi-Fi do local.
// Personalize antes de gravar (minimo 8 caracteres).
const char* portalPassword = "config-esp32";
char portalName[32];
DHT dht(DHTPIN, DHTTYPE);
WebServer server(80);
unsigned long disconnectedSince = 0;
bool waitingForNetwork = false;
unsigned long lastSample = 0;
unsigned long lastUpload = 0;
float temperaturaAtual = NAN;
float umidadeArAtual = NAN;
int soloAtual = 0;
time_t measuredAt = 0;
const unsigned long SAMPLE_INTERVAL_MS = 3000;

bool validDeviceId() {
  String id = DEVICE_ID;
  if (id.length() == 0 || id.length() > 64) return false;
  for (size_t i = 0; i < id.length(); i++) {
    char c = id[i];
    if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
          (c >= '0' && c <= '9') || c == '_' || c == '-')) return false;
  }
  return true;
}

void readSensors() {
  temperaturaAtual = dht.readTemperature();
  umidadeArAtual = dht.readHumidity();
  soloAtual = analogRead(SENSOR_SOLO);
  measuredAt = time(nullptr);
}

void uploadMeasurement() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (measuredAt < 1760000000) {
    Serial.println("Envio aguardando horario NTP. Verifique acesso a internet e UDP 123.");
    return;
  }
  if (!isfinite(temperaturaAtual) || !isfinite(umidadeArAtual) ||
      umidadeArAtual < 0 || umidadeArAtual > 100) {
    Serial.println("Amostra descartada: leitura invalida do DHT11.");
    return;
  }
  String base = API_BASE_URL;
  while (base.endsWith("/")) base.remove(base.length() - 1);
  if (!base.startsWith("https://") || strlen(INGEST_API_KEY) == 0 || !validDeviceId()) {
    Serial.println("Envio desativado: confira URL HTTPS, chave e dispositivo em secrets.h.");
    return;
  }
  struct tm utc;
  gmtime_r(&measuredAt, &utc);
  char timestamp[25];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
  String payload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"temperature_c\":";
  payload += String(temperaturaAtual, 1);
  payload += ",\"air_humidity_pct\":" + String(umidadeArAtual, 1);
  payload += ",\"soil_raw\":" + String(soloAtual);
  payload += ",\"measured_at\":\"" + String(timestamp) + "\"}";

  NetworkClientSecure secure;
  // ESP32 Arduino core 3.3.12: validate hostname and chain with built-in roots.
  secure.useBuiltinCACertBundle();
  secure.setHandshakeTimeout(15);
  HTTPClient http;
  http.setConnectTimeout(15000);
  http.setTimeout(60000);  // Allow the Free Render service to wake up.
  http.setReuse(false);
  if (!http.begin(secure, base + "/api/v1/measurements")) {
    Serial.println("Falha ao preparar conexao HTTPS.");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", INGEST_API_KEY);
  int code = http.POST(payload);
  if (code == 201) {
    Serial.printf("Medicao enviada diretamente para a nuvem: HTTP 201, solo=%d, horario=%s\n", soloAtual, timestamp);
  } else if (code == 401) {
    Serial.println("API recusou a chave: HTTP 401. Confira INGEST_API_KEY em secrets.h e na Render.");
  } else if (code > 0) {
    Serial.printf("API retornou HTTP %d. Amostra nao confirmada.\n", code);
  } else {
    Serial.printf("Falha HTTPS (%d): verifique DNS, internet, horario e certificado.\n", code);
  }
  http.end();
  // No retry of this sample: POST may have succeeded even if the reply timed out.
}

void paginaInicial() {
  float temperatura = temperaturaAtual;
  float umidadeAr = umidadeArAtual;
  int leitura = soloAtual;
  int umidadeSolo = constrain(map(leitura, SOLO_SECO, SOLO_MOLHADO, 0, 100), 0, 100);

  String html = "<html><head>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<meta http-equiv='refresh' content='3'>";
  html += "<style>body{font-family:Arial;background:#101827;color:white;text-align:center;padding:20px;}";
  html += ".card{background:#1e293b;padding:25px;margin:15px auto;border-radius:15px;max-width:350px;}";
  html += "h1{color:#38bdf8;}</style></head><body><h1>Monitoramento ESP32</h1>";
  html += "<div class='card'><h2>Temperatura</h2>";
  if (isnan(temperatura)) html += "Erro no sensor";
  else html += String(temperatura, 1) + " C";
  html += "</div><div class='card'><h2>Umidade do ar</h2>";
  if (isnan(umidadeAr)) html += "Erro no sensor";
  else html += String(umidadeAr, 1) + " %";
  html += "</div><div class='card'><h2>Umidade do solo</h2>";
  html += String(umidadeSolo) + " %";
  html += "<p>Leitura: " + String(leitura) + "</p>";
  if (umidadeSolo < 30) html += "<p>Solo seco!</p>";
  else if (umidadeSolo < 70) html += "<p>Solo umido</p>";
  else html += "<p>Solo molhado</p>";
  html += "</div></body></html>";
  server.send(200, "text/html; charset=utf-8", html);
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.mode(WIFI_STA);
  snprintf(portalName, sizeof(portalName), "Ambiente-ESP32-%06lX",
           (unsigned long)(ESP.getEfuseMac() & 0xFFFFFF));

  WiFiManager manager;
  manager.setConnectTimeout(20);
  manager.setConfigPortalTimeout(300);
  Serial.println("Tentando a rede salva. Se falhar, conecte-se a:");
  Serial.println(portalName);
  Serial.println("No modo configuracao, abra http://192.168.4.1");
  // Credenciais da rede escolhida sao persistidas pelo WiFiManager.
  // O portal usa a porta 80 apenas antes de iniciar nosso painel.
  if (!manager.autoConnect(portalName, portalPassword)) {
    Serial.println("Configuracao nao concluida. Reiniciando para tentar novamente.");
    delay(1000);
    ESP.restart();
    return;
  }
  WiFi.setAutoReconnect(true);
  WiFi.setSleep(false);
  configTime(0, 0, "pool.ntp.org", "time.google.com", "time.cloudflare.com");
  Serial.println("Sincronizacao UTC por NTP iniciada. Envio direto HTTPS a cada 30 segundos.");
  lastSample = millis() - SAMPLE_INTERVAL_MS;
  lastUpload = millis() - UPLOAD_INTERVAL_MS;
  Serial.print("Wi-Fi conectado. Endereco IP: ");
  Serial.println(WiFi.localIP());
  Serial.println("Digite w no Monitor Serial para apagar o Wi-Fi salvo e reconfigurar.");
  server.on("/", paginaInicial);
  server.begin();
}

void loop() {
  // Troca voluntaria mesmo quando a rede antiga ainda esta disponivel.
  if (Serial.available() && Serial.read() == 'w') {
    server.stop();
    WiFiManager manager;
    manager.resetSettings();
    Serial.println("Wi-Fi salvo removido. Reiniciando para configurar outra rede.");
    delay(500);
    ESP.restart();
    return;
  }
  if (WiFi.status() == WL_CONNECTED) {
    waitingForNetwork = false;
    if (millis() - lastSample >= SAMPLE_INTERVAL_MS) {
      lastSample = millis();
      readSensors();
    }
    server.handleClient();
    if (millis() - lastUpload >= UPLOAD_INTERVAL_MS) {
      lastUpload = millis();
      uploadMeasurement();
    }
  } else {
    if (!waitingForNetwork) {
      waitingForNetwork = true;
      disconnectedSince = millis();
      Serial.println("Wi-Fi desconectado. Aguardando reconexao por ate 60 segundos.");
    }
    // Reinicia para autoConnect reabrir o portal se a rede continuar indisponivel.
    if (millis() - disconnectedSince >= 60000UL) {
      ESP.restart();
      return;
    }
  }
  delay(2);
}
