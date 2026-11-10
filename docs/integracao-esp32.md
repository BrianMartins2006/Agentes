# Modos de integração da ESP32

## Envio direto — modo recomendado atual

O firmware em `firmware/monitoramento_ambiental/` agora envia medições por HTTPS
diretamente à Render, sem depender da comunicação local com um computador.
Configuração da chave, versão do core, Wi-Fi, NTP e teste em hardware estão em
[`firmware/README.md`](../firmware/README.md).

Antes de gravar essa versão, pare o coletor Python. Após conectar e sincronizar o
relógio, confira `HTTP 201` no Monitor Serial. Não é necessário alterar o IP no
`.env` quando trocar de rede. Esse IP continua útil apenas para o painel local.
A placa precisa de internet liberada; isolamento entre clientes não é a mesma coisa
que bloqueio de saída HTTPS ou NTP. O teste físico do envio direto ainda está pendente.

## Coletor local — modo alternativo legado

O conteúdo abaixo descreve o fluxo original, ainda disponível para firmware antigo.
Não executar o coletor simultaneamente ao envio direto para o mesmo dispositivo.

### Contrato original

## Contrato confirmado pelo código fornecido

- DHT11 no GPIO4: temperatura em °C e umidade do ar em %.
- Sensor de solo no GPIO34: leitura bruta em `Leitura: N`.
- HTTP porta 80, rota `/`, resposta HTML com três elementos `div.card`.
- A página solicita atualização a cada 3 segundos quando aberta no navegador.
- O firmware não oferece rota JSON, envio à API ou timestamp de amostra.
- Calibração informada no firmware: seco = 4095; molhado = 2901.
  O percentual é calculado por `map` e limitado ao intervalo de 0 a 100.
  Esses valores devem ser validados fisicamente para o sensor e solo usados.

O coletor não armazena nem utiliza as credenciais Wi-Fi do código fornecido.
Após autorização, foi criado um sketch com configuração Wi-Fi pelo celular em
`firmware/`. O contrato HTML foi preservado. A versão mais recente também envia diretamente à nuvem.

## Funcionamento do coletor

1. Lê `ESP32_URL` com timeout HTTP de 10 segundos.
2. Localiza os três cartões e extrai temperatura, umidade do ar e leitura bruta.
3. Valida os dados com o mesmo schema da API. Se faltar um campo, houver cartão
   duplicado, formato inesperado ou erro do DHT11, descarta a amostra completa.
4. Usa o horário UTC do computador após receber a página como `measured_at`.
   Esse é o instante de coleta, não um horário informado pelo dispositivo.
5. Envia a amostra à API com `X-API-Key`, somente nessa requisição ao backend.
   O banco registra também `received_at`, horário de chegada.
6. Aguarda `POLL_SECONDS` (10 por padrão, mínimo de 3) antes do próximo ciclo.

O percentual do solo exibido no painel não é persistido nesta versão. Preservar
`soil_raw` permite recalcular o percentual posteriormente. Antes de usar percentuais
em análises, versionar a calibração por dispositivo e período de validade.

## Executar

Consulte os comandos completos no README da raiz. No `.env`, configure:

```dotenv
ESP32_URL=http://192.168.1.100/
DEVICE_ID=esp32-01
API_BASE_URL=http://127.0.0.1:8000
POLL_SECONDS=10
```

O IP acima é ilustrativo. Use o IP impresso no Monitor Serial a 115200 baud e
confirme que o computador consegue abrir a página. Use os mesmos `INGEST_API_KEY`
e banco da API. O coletor é executado de `backend/`, com o ambiente virtual ativo:

```bash
python -m app.collector --once
python -m app.collector
```

`--once` encerra com código 1 se a coleta falhar. No modo contínuo, falhas são
registradas sem conteúdo da página ou credenciais, e o próximo ciclo tenta obter
uma nova amostra. Não há fila local nem reenvio de amostra após falha: um timeout
no POST pode ocorrer depois de a API já ter persistido a medição. A API ainda não
possui deduplicação. Medições feitas durante indisponibilidade podem ser perdidas.

## Limites e próximos passos

O parser depende dos títulos e da estrutura HTML do firmware fornecido. Mudanças
no painel exigem revisão do parser. A comunicação é feita pelo computador na rede
local; o IP da ESP32 pode mudar conforme a configuração do roteador. O hardware
real e a conexão com PostgreSQL ainda precisam de teste integrado.

A evolução pode incluir registro versionado da calibração, identificação de
amostras para reenvio seguro, fila persistente e dashboard. Qualquer mudança no
firmware exige autorização explícita do usuário.
