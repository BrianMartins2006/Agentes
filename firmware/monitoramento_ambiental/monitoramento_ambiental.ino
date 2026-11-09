#include <WiFi.h>
#include <WebServer.h>
#include <WiFiManager.h>
#include <DHT.h>

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

void paginaInicial() {
  float temperatura = dht.readTemperature();
  float umidadeAr = dht.readHumidity();
  int leitura = analogRead(SENSOR_SOLO);
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
    server.handleClient();
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
