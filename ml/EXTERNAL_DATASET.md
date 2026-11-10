# Experimento público de umidade do solo

Foi treinado um Random Forest com dados reais de campo da Universidade de Ioannina,
sem inventar variações ou inserir medições externas na tabela da ESP32.

## Origem e licença

Salmas, D.; Kapsala, O.; Giavis, I.; Pachoulas, G.; Stylios, C. (2026).
**Ten-Minute Atmospheric and Soil-Moisture Time Series for the Arta Pilot, Greece
(2015–2026)**, versão 1. DOI: https://doi.org/10.5281/zenodo.21703750.
Licença CC BY 4.0. Fonte e arquivos: https://zenodo.org/records/21703750.

Usamos a estação **Kompoti**, solo a **10 cm**, temperatura do ar e umidade relativa.
O README da fonte informa umidade em %. Kampi foi excluída porque a documentação
informa solo em milímetros nessa estação. Não misturamos estações nem profundidades.
Os horários originais são preservados: o fuso não é explicitado na documentação.

## Preparação reproduzível

- Verificação do MD5 do ZIP publicado; SHA-256 incluído no relatório.
- Junção das três séries pelo timestamp exato, a cada 10 minutos.
- Exclusão de ausências, valores não finitos, solo/umidade fora de 0–100%,
  temperatura fora de −40 a 60 °C e duplicatas com valores conflitantes.
- Uso das últimas 10.000 observações alinhadas disponíveis. O relatório informa
  janela temporal, contagens e limites; o processo não preenche lacunas.
- Atributos: solo atual (%), temperatura (°C), umidade do ar (%), solo de 30 minutos
  antes (%) e variação em 30 minutos (pontos percentuais).
- Alvo: solo 30 minutos à frente (%). Cada exemplo exige continuidade de todos os
  pontos desde 30 minutos antes até 30 minutos depois.
- Primeiros 75% das janelas para treino, últimos 25% para teste; purga entre o alvo
  de treino e a janela de atributos do teste. Não há ajuste no teste nem seleção
  de hiperparâmetros pelos resultados do teste.
- Random Forest: 100 árvores, profundidade 8, mínimo 3 amostras/folha e semente 42.

## Resultado obtido

| Método | MAE (pontos percentuais) | RMSE (pontos percentuais) |
|---|---:|---:|
| Random Forest | 0,107816 | 0,147678 |
| Persistência: manter o solo atual | 0,019832 | 0,044712 |

Treino: 7.480 exemplos; teste: 2.496. **O modelo não superou a persistência**.
Como o solo muda pouco em 30 minutos nesse período, prever manutenção do valor é
uma referência forte. Erro absoluto pequeno sozinho não demonstra utilidade do ML.
Não modificamos o conjunto de teste para tentar melhorar artificialmente o resultado.

O relatório detalhado está em `ml/reports/external-soil.json`, incluindo exemplos
históricos de previsão, variação, métricas, parâmetros e hashes. As árvores foram
salvas na tabela `forecast_models` com identificador separado
`external-arta-kompoti-10cm`; os arquivos numéricos originais não são versionados.

## Reproduzir

Baixe `dataset-grecia.zip` na página do Zenodo. Com o ambiente virtual ativo,
execute dentro de `backend/`:

```bash
python -m app.train_external --archive /caminho/dataset-grecia.zip
```

Para salvar uma nova versão do experimento no banco configurado no `.env`:

```bash
python -m app.train_external --archive /caminho/dataset-grecia.zip --publish
```

O ZIP é conferido contra a versão 1 publicada. O treino não precisa da placa e não
altera as medições ou o modelo nativo do dispositivo. Novos dados externos exigem
execução explícita desse comando; o agendador da API continua dedicado às medições
coletadas no projeto.

## Painel e limites

A API expõe `GET /api/v1/experiments/soil`, com `X-API-Key`, retornando o relatório
sem as árvores. O React exibe uma seção **Experimento separado — Dataset público**,
com métricas e exemplos históricos. Exige publicar a nova versão da API e do React.

Este experimento **não é uma previsão validada para a ESP32**: porcentagem de um
sensor de campo a 10 cm não equivale à leitura bruta 0–4095 ou à porcentagem por
mapeamento seco/molhado da placa. Não fazemos conversão inventada entre essas
escalas, não reescrevemos datas para simular leituras atuais e não treinamos com
os dados do teste. Transferência para a placa exigiria calibração e avaliação real.

O enunciado pede treinamento/avaliação com os dados coletados pelo projeto. A base
pública complementa a entrega; substituir totalmente essa parte exige alinhamento
com o professor. O próximo experimento pode avaliar outro horizonte com novos
períodos de validação e teste, ou prever temperatura com os dados reais do DHT11.
