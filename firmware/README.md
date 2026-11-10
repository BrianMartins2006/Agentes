# ESP32: Wi-Fi configurável e envio direto HTTPS

O firmware lê DHT11 no GPIO4 e solo no GPIO34, mantém o painel local e envia
medições diretamente para o FastAPI na Render. Não precisa de coletor Python nem
de acesso do computador ao IP da placa. O Wi-Fi ainda precisa permitir internet,
HTTPS (porta 443), DNS e sincronização NTP (UDP 123).

## Preparar no Arduino IDE

1. Use o suporte **ESP32 da Espressif 3.3.12**, usado na compilação desta versão.
   O método de certificados `useBuiltinCACertBundle()` depende desse suporte.
2. Instale **WiFiManager**, de tzapu, **DHT sensor library**, da Adafruit, e
   **Adafruit Unified Sensor**.
3. Abra `monitoramento_ambiental/monitoramento_ambiental.ino`.
4. Confira o arquivo `secrets.h` na mesma pasta. Ele foi preparado localmente a
   partir da chave do `.env` e está ignorado pelo Git. Em outro computador, copie
   `secrets.example.h` para `secrets.h` e preencha:

```cpp
#define API_BASE_URL "https://ambiente-api.onrender.com"
#define INGEST_API_KEY "CHAVE_IGUAL_A_DA_RENDER"
#define DEVICE_ID "esp32-01"
#define UPLOAD_INTERVAL_MS 30000UL
```

5. Personalize `portalPassword` no sketch se necessário. Essa senha é apenas da
   rede temporária da placa; não é a chave da API ou a senha do Wi-Fi do local.
6. Selecione sua ESP32 e porta USB, compile e grave. Abra o Monitor Serial a 115200.

Não publique `secrets.h` nem binários contendo a chave. O backend continua sendo o
único componente com senha do PostgreSQL. Se mudar a chave da API na Render,
atualize `secrets.h` e grave novamente. A chave atual do projeto é compartilhada;
autenticação específica por dispositivo continua uma melhoria futura.

## Trocar de rede

A placa tenta o Wi-Fi salvo por até 20 segundos. Se falhar, abre a rede
`Ambiente-ESP32-XXXXXX`. Conecte o celular usando `portalPassword`, aceite ficar
sem internet e abra http://192.168.4.1. Em **Configure WiFi**, escolha a rede e
informe a senha. O portal pode ficar aberto por até 5 minutos; sem configurar, a
placa reinicia e tenta de novo. As credenciais válidas ficam salvas na placa.

Se a conexão cair durante o funcionamento, tenta reconectar e reinicia após
60 segundos sem rede para reabrir o fluxo de configuração. O comando `w` no Monitor
Serial apaga o Wi-Fi salvo e reinicia, útil para trocar voluntariamente de rede.
Esse comando é processado no loop, após eventual requisição HTTPS em andamento.

O novo IP só serve para acessar o painel local. Não é mais necessário atualizar
`ESP32_URL` para o envio direto. Mesmo se o campus isolar os dispositivos entre si,
a placa pode enviar à nuvem, desde que a própria placa tenha acesso à internet.
Uma rede com página de login, autenticação institucional não configurada ou
bloqueios de portas ainda pode impedir esse envio.

## Conferir o envio

Depois de conectar, o Serial mostra a sincronização UTC por NTP. Com o relógio
sincronizado, deve aparecer a cada ciclo:

```text
Medicao enviada diretamente para a nuvem: HTTP 201, solo=..., horario=...
```

- `Envio aguardando horario NTP`: sem relógio válido, não envia timestamp inventado.
  Verifique acesso a NTP ou teste uma rede com internet sem bloqueios.
- `HTTP 401`: chave diferente da configurada na API.
- Outro código HTTP: consultar o estado da API e os logs da Render.
- `Falha HTTPS`: verificar internet, DNS, relógio e certificado.
- DHT11 inválido: a amostra inteira é descartada.

A validação TLS usa o bundle de certificados do core, sem `setInsecure()`.
A requisição tem timeout de conexão de 15 s, handshake de 15 s e leitura de 60 s
para acomodar a inicialização da Render Free. Durante o POST síncrono, o painel
local e comandos seriais podem ficar temporariamente sem resposta. É uma primeira
implementação simples; separar a comunicação em tarefa própria é uma evolução.

Não há fila persistente nem reenvio da mesma amostra após erro: um POST pode ter
sido salvo mesmo que a resposta se perca. O próximo ciclo obtém uma nova leitura.
Não execute simultaneamente o coletor Python para o mesmo dispositivo, para evitar
medições duplicadas. Pare-o com Ctrl+C antes de testar o firmware direto.

## Fluxo completo

Sensores → ESP32 → Wi-Fi com internet → HTTPS Render → PostgreSQL Supabase →
dashboard React na Vercel. O modelo continua no backend, sem treinamento na placa.
O computador só é necessário para programar e acompanhar o Serial; depois a placa
precisa de alimentação e internet. A dashboard consulta atualizações a cada 30 s.

## Validação em hardware pendente

A compilação não substitui o teste físico. Após gravar, verificar: configuração
Wi-Fi, sincronização NTP, HTTP 201, incremento no banco/painel, erro de chave,
queda da rede e reconexão. Se NTP/HTTPS forem bloqueados no campus, solicitar acesso
apropriado ou usar um hotspot autorizado em 2,4 GHz com internet.

Referência: [WiFiManager](https://github.com/tzapu/WiFiManager) e
[NetworkClientSecure oficial](https://github.com/espressif/arduino-esp32/tree/master/libraries/NetworkClientSecure).
