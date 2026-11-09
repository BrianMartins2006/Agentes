# Previsão de umidade do solo — primeira implementação

O código de treino e inferência está implementado. **Ainda não há modelo treinado
com leituras reais da placa, nem métricas de campo.** Os testes usam dados
sintéticos isolados, que não são inseridos no histórico da aplicação.

## O que o modelo aprende

Prevê a leitura bruta do sensor de solo daqui a 30 minutos, usando:

- leitura atual do solo;
- temperatura e umidade do ar atuais;
- leitura do solo de cinco minutos atrás;
- variação do solo nos últimos cinco minutos.

Algoritmo: `RandomForestRegressor` do scikit-learn, com 100 árvores, profundidade
máxima 8, pelo menos 3 exemplos por folha e `random_state=42`. Os parâmetros são fixos
nesta primeira versão; não houve busca de hiperparâmetros no conjunto de teste.
O percentual exibido na previsão é uma conversão estimada com os pontos do
firmware (seco 4095, molhado 2901), limitado entre 0 e 100. O alvo de treino e as
métricas continuam sendo a leitura bruta, não uma medição física certificada de
umidade. Validar a calibração em campo. Ao mudar sensor/calibração ou ambiente,
separar a coleta pelo identificador do dispositivo/experimento e treinar novamente.
A primeira versão não possui registro temporal de calibrações.

## Preparação e avaliação

1. Buscar as últimas 100.000 linhas do dispositivo por padrão, com limite ajustável.
2. Converter amostras em médias de minutos completos, com horário UTC no fim de
   cada minuto. Nenhuma leitura de um minuto futuro ou ainda incompleto é usada.
3. Exigir seis minutos consecutivos para os atributos. Para treino, exigir também
   continuidade até o alvo 30 minutos à frente. Não interpolar grandes lacunas.
4. Separar os primeiros 75% das janelas para treino e os últimos 25% para teste.
   Purgar exemplos de treino cujo alvo alcance a janela de atributos do teste.
5. Ajustar a floresta somente no treino, sem normalização dos atributos. Não refazer o ajuste com o
   teste após avaliá-lo; o modelo salvo é exatamente o modelo avaliado.
6. Comparar MAE e RMSE com persistência: prever o solo futuro igual ao valor atual.
   Métricas menores são melhores; ambas estão em unidades da leitura bruta.
7. Armazenar árvores em JSON, importância dos atributos, parâmetros, versão, datas,
   número de exemplos, hash do dataset preparado, limites e métricas no PostgreSQL.

Exige pelo menos 120 janelas válidas, 60 de treino após purga e 20 de teste, além
de variação no solo. Esses limites são apenas verificações técnicas, não prova de
qualidade científica. Coletar vários ciclos reais de secagem e rega, em diferentes
condições, antes de apresentar resultados. Uma série curta e muito correlacionada
pode produzir métricas boas sem generalizar. Avaliar futuramente em múltiplos
blocos temporais e em um período de campo adicional, sem reajustar no teste.

## Executar com a base real

Ative o ambiente virtual na raiz e instale as dependências atualizadas:

```bash
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend
alembic upgrade head
python -m app.train_model --device-id esp32-01
```

O `.env` deve apontar para o banco com as medições reais. O comando não fabrica
dados. Se não houver histórico suficiente, termina com código 2, explica o motivo
e não salva modelo. Quando funciona, imprime um relatório JSON e salva uma versão
na tabela `forecast_models`. Guarde também a exportação das medições do experimento
para reproduzir o treino: o hash identifica o dataset, mas não substitui a base.

Ajustar o máximo de linhas se necessário:

```bash
python -m app.train_model --device-id esp32-01 --limit 200000
```

O treino automático é iniciado junto da API e verifica cada dispositivo a cada
5 minutos. Após o primeiro modelo, exige ao menos uma hora desde o último treino
e 120 novas linhas de medição. Dados insuficientes não geram modelos fictícios.
Também é possível executar o comando manual para um experimento controlado. A última versão treinada é usada, mesmo se experimental; não há
promoção automática condicionada à melhoria de um modelo já existente.

## API e dashboard

`GET /api/v1/predictions?device_id=esp32-01` exige `X-API-Key` e retorna:

- `unavailable`: modelo ausente, dados insuficientes, lacunas ou atraso maior que
  cinco minutos; não retorna previsão fictícia;
- `available`: modelo treinado, leituras recentes e MAE menor que o baseline no teste;
- `experimental`: modelo treinado, mas sem superar a persistência no teste.

Uma previsão disponível informa instante-base, instante-alvo, horizonte, leitura
prevista, percentual estimado, calibração, versão, métricas e aviso. O instante-alvo
é 30 minutos após o fim do último minuto completo, não exatamente 30 minutos após
a abertura da tela. A consulta não grava previsões nem envia notificações externas.

O aviso de possível solo seco deriva da previsão do modelo e da conversão para
percentual abaixo de 30%. O limiar apenas interpreta uma previsão aprendida; não
substitui o ML. Não há atuação física ou irrigação automática. O sistema não produz
probabilidade ou intervalo de confiança, pois eles ainda não foram estimados.

Abra a dashboard React em `http://127.0.0.1:5173/` após iniciar Vite e API. Ela mostra a
previsão junto de valores atuais, gráficos, filtros e comparação com o baseline.

## Relação com o enunciado

Esta implementação cobre o código de treino/avaliação, a API de inferência e a
exibição do resultado. Para demonstrar atendimento completo ainda precisamos:
coleta real suficiente, modelo treinado e avaliado, análise dos resultados,
integração hospedada, relatório e demonstração de previsão ou aviso.

Referências: [RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
e [prevenção de vazamento entre treino e teste](https://scikit-learn.org/stable/common_pitfalls.html).


## Troca para Random Forest

Escolhido por alinhamento com o conteúdo estudado em aula. A previsão é a média
produzida por múltiplas árvores de decisão. As importâncias dos atributos ficam no
relatório do treino e indicam contribuição ao modelo, não causalidade.

Artefatos antigos de Ridge são mantidos no histórico, mas não são usados para
inferência. Execute novamente `python -m app.train_model --device-id esp32-01`
para salvar a versão Random Forest (schema 2). A tabela e a API permanecem iguais;
não é necessária migração adicional do banco.

Florestas têm dificuldade para extrapolar além dos valores observados no treino.
Por isso, coletar vários ciclos de secagem e rega é essencial. A escolha não garante
superar a persistência: a avaliação temporal mantém o resultado experimental quando
não há melhoria de MAE. Não treinar novamente repetidamente para escolher o melhor
resultado no mesmo teste; reservar novos períodos para avaliação futura.


## Automação operacional

Configurações do backend (com valores padrão):

```dotenv
ML_AUTO_TRAIN_ENABLED=true
ML_CHECK_SECONDS=300
ML_RETRAIN_SECONDS=3600
ML_MIN_NEW_SAMPLES=120
```

O treino roda numa thread fora do processamento HTTP, um ciclo de cada vez.
Modelos e o ID da última amostra considerada ficam no PostgreSQL para sobreviver a
reinícios. Transações com advisory locks impedem dois workers PostgreSQL de treinar
automaticamente o mesmo dispositivo simultaneamente. Esse lock precisa de conexão
com suporte a transações, como o Session Pooler indicado para o Supabase.

A API deve estar em execução: se a Render suspender a instância Free, a verificação
também para e retoma na próxima inicialização. Para autonomia contínua, utilizar
uma instância sempre ativa ou separar o treino num worker/agendador. Não existe
execução de treinamento no navegador ou na Vercel. O comando manual não participa
do lock do agendador; evitar executá-lo ao mesmo tempo que o ciclo automático.

O modelo mais recente é publicado mesmo quando experimental; as métricas e o aviso
indicam quando ele não supera a persistência. Não há seleção automática de modelos
por resultados repetidos no teste. Cada retreino é uma nova avaliação temporal;
a qualidade ainda precisa de confirmação num período de campo independente.
