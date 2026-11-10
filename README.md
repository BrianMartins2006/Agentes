# Monitoramento ambiental IoT

Base inicial para ESP32 + FastAPI + PostgreSQL. Após autorização, foi preparado
um firmware com configuração de Wi-Fi pelo celular; ainda não foi gravado na placa.
Veja [`firmware/README.md`](firmware/README.md).
O coletor HTML, a dashboard e o código de ML estão implementados. O treino com
dados reais e a validação integrada em hardware/nuvem ainda estão pendentes.

## 1. Entender a arquitetura

ESP32 (DHT11 GPIO4, solo GPIO34) → coletor HTML → API FastAPI → PostgreSQL.
A dashboard consultará a API; o ML usará o histórico validado.
O painel Wi-Fi atual continua funcionando de forma independente.

O atendimento ao enunciado está mapeado em
[`docs/requisitos-trabalho.md`](docs/requisitos-trabalho.md), com PEAS, requisitos,
pendências, proposta de ML e critérios de demonstração. O projeto ainda está em
desenvolvimento e não atende integralmente aos requisitos.

Para consultar diariamente o histórico do Supabase, foi preparado o comando
`python -m app.daily_check`. Veja a configuração do agendamento e suas limitações
em [`docs/consulta-diaria.md`](docs/consulta-diaria.md). Nenhum job foi ativado.

## 2. Conhecer a estrutura

- `backend/app`: configuração, conexão, tabela, validação e rotas HTTP.
- `backend/migrations`: evolução versionada do banco com Alembic.
- `backend/app/collector.py`: lê o HTML existente da ESP32 e envia medições à API.
- `backend/tests`: testes da API com SQLite e do coletor com HTTP simulado.
- `compose.yaml`: PostgreSQL local com volume persistente.
- `docs/integracao-esp32.md`: informações necessárias para conectar o dispositivo.
- `dashboard/`: interface web com gráficos, filtros e previsão.
- `ml/`: guia de treinamento e avaliação; implementação em `backend/app/forecasting.py`.

## 3. Preparar o ambiente

Requisitos: Python 3.11+ e Docker com Compose. Execute a partir desta pasta:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
docker compose up -d db
```

Edite `.env` para escolher a chave da API e as credenciais locais. Se mudar a senha,
atualize também `DATABASE_URL` (caracteres especiais precisam de codificação na URL).
Não versione `.env`. As dependências têm faixas compatíveis; ainda não há lockfile.

## 4. Criar o banco e iniciar a API

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

O Alembic cria a tabela e os índices; a API não altera o esquema automaticamente.
Para a dashboard React, em outro terminal execute `cd dashboard && npm ci && npm run dev`
a partir da raiz. Abra http://127.0.0.1:5173/ e informe a chave da API.
Abra http://127.0.0.1:8000/docs para explorar e testar as rotas.
Use **Authorize** para informar a chave de `.env`.
`GET /health` verifica apenas o processo da API, não a conexão com o banco.

## 5. Enviar uma medição manual

Em outro terminal, substitua o valor da chave abaixo pelo configurado em `.env`:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/measurements \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-this-local-key' \
  -d '{"device_id":"esp32-01","temperature_c":25,"air_humidity_pct":65,"soil_raw":2100,"measured_at":"2026-11-09T12:00:00Z"}'

curl 'http://127.0.0.1:8000/api/v1/measurements?device_id=esp32-01&limit=100' \
  -H 'X-API-Key: change-this-local-key'
```

O exemplo é sintético. A API retorna leituras da mais recente à mais antiga, aceita
`since` e `until` com fuso horário, `limit` (até 1000) e `offset`. Para gráficos, ordenar o
resultado cronologicamente. `measured_at` é o horário da amostra; `received_at` é a
chegada ao banco. O PostgreSQL armazena ambos com suporte a fuso horário.
Umidade do ar é percentual; solo é leitura bruta, sem calibração presumida.

## 6. Verificar a base

Com o ambiente virtual ativo, dentro de `backend/`:

```bash
python -m pytest -q
alembic upgrade head --sql
```

Os testes verificam persistência, filtros, autenticação e entradas inválidas usando
SQLite; o coletor usa respostas HTTP simuladas. Não substituem um teste de
integração com PostgreSQL e ESP32 reais. Para essa
verificação, suba o banco, aplique a migração e execute os exemplos HTTP acima.

## 7. Conectar a ESP32 e avançar

O firmware fornecido expõe HTML em `http://IP_DA_ESP32/`. Configure `ESP32_URL`
no `.env` com o IP exibido no Monitor Serial (115200 baud). O computador deve
conseguir acessar esse endereço pela rede. Se seu `.env` foi criado antes do
coletor, acrescente `ESP32_URL`, `DEVICE_ID`, `API_BASE_URL` e `POLL_SECONDS`
conforme `.env.example`, preservando suas credenciais.

Com banco e API em execução, abra outro terminal, ative o ambiente virtual e,
dentro de `backend/`, execute:

```bash
python -m app.collector --once
python -m app.collector
```

O primeiro comando testa uma coleta; o segundo mantém a coleta contínua (10 segundos
entre ciclos por padrão). Use Ctrl+C para encerrar. Não execute múltiplas instâncias
para o mesmo dispositivo, pois não há deduplicação. O coletor é compatível com o HTML original e com o novo firmware de configuração
Wi-Fi em `firmware/`. O fluxo e as limitações estão em `docs/integracao-esp32.md`.

A dashboard já exibe gráficos, filtros, estado e a saída do ML quando disponível.
Para treinar com o histórico real, dentro de `backend/`, execute:

```bash
python -m app.train_model --device-id esp32-01
```

Aplique `alembic upgrade head` antes: a migração 0002 cria o armazenamento dos
modelos. Veja [`ml/README.md`](ml/README.md) para entender atributos, horizonte,
preparação, separação temporal e comparação com baseline. Sem histórico suficiente,
o comando não treina e a dashboard informa que o modelo está indisponível.
Não há modelo real ou métricas de campo apresentados nesta entrega.

A configuração é para desenvolvimento local. Acesso remoto exige configuração de
HTTPS e gestão de acesso. O banco está publicado apenas em localhost. Para parar
sem apagar as medições, execute `docker compose stop` na raiz.

Referências: [FastAPI e bancos relacionais](https://fastapi.tiangolo.com/tutorial/sql-databases/)
e [SQLAlchemy com PostgreSQL/psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg).


## Frontend Vercel e treino automático

A dashboard foi migrada para React/Vite. Veja [`dashboard/README.md`](dashboard/README.md)
para configurar a Vercel, a URL pública da API e o CORS da Render. O frontend só
recebe medições e previsões via API; banco e treinamento ficam no backend.

O treino automático está habilitado por padrão durante a execução da API. A cada
5 minutos verifica o histórico; para retreinar exige intervalo de uma hora e 120
novas medições. Os requisitos de continuidade/variação do dataset também se aplicam.
Veja [`ml/README.md`](ml/README.md). Nenhum deploy foi realizado nesta etapa.


## Deploy da API e proteção do Supabase

A configuração da Render está em `render.yaml`. Siga
[`docs/deploy-render.md`](docs/deploy-render.md) para conectar o repositório e
configurar os segredos. A migração `0003` habilita RLS em `measurements`,
`forecast_models` e `alembic_version`, sem políticas públicas. O acesso direto do
backend com o proprietário do banco é preservado.


## Envio direto pela ESP32

O firmware atual implementa envio HTTPS direto à Render a cada 30 segundos, com
validação TLS e horário UTC via NTP. Consulte [`firmware/README.md`](firmware/README.md)
para preparar `secrets.h` e gravar na placa. Este modo dispensa o coletor local e a
configuração de IP na troca de rede. O teste em hardware ainda precisa ser realizado;
pare o coletor Python antes para evitar duplicação de amostras.
