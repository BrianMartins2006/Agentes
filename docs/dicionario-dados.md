# Dicionário de dados

## measurements — uma linha por amostra

| Campo | Tipo | Unidade/origem |
|---|---|---|
| id | inteiro, chave primária | Identificador gerado pelo banco |
| device_id | texto até 64 | Ex.: esp32-01; não é IP nem senha |
| temperature_c | número real | Temperatura do ar em °C, DHT11 |
| air_humidity_pct | número real entre 0 e 100 | Umidade relativa do ar em %, DHT11 |
| soil_raw | inteiro não negativo | Leitura analógica, sem unidade física; GPIO34 |
| measured_at | timestamp com fuso | Instante da medição, UTC/NTP no firmware direto |
| received_at | timestamp com fuso | Instante de chegada, gerado no PostgreSQL |

O histórico inicial via coletor usa horário UTC do computador. No envio direto,
usa UTC da ESP32 sincronizado por NTP. O schema atual não armazena um campo separado
para a origem do relógio; identificar essa transição pelos registros da implantação.
Valores brutos do solo não são reescritos ao recalibrar. O percentual mostrado é
estimado por 4095 seco/2901 molhado, limitado a 0–100; não é umidade volumétrica
certificada. A calibração temporal por dispositivo ainda não é versionada.

## forecast_models — versões independentes de modelos

| Campo | Tipo | Conteúdo |
|---|---|---|
| id | UUID em texto | Identificador de uma versão |
| device_id | texto | Dispositivo real ou identificador do experimento externo |
| trained_at | timestamp com fuso | Horário em que o artefato foi salvo |
| artifact | JSON | Modelo, alvo, atributos, parâmetros, hashes, datas, métricas e árvores |

No JSON: `target=soil_raw` (schema 2) ou `target=temperature_c` (schema 3).
Artefatos antigos sem alvo são tratados como solo. Consultas filtram alvo, sem
sobrescrever um modelo de solo com um de temperatura. O experimento externo possui
identificador e schema próprios e não orienta irrigação da placa.

MAE/RMSE em °C para temperatura, leitura bruta para solo nativo e pontos percentuais
para solo externo. `beats_baseline` compara MAE no teste cronológico. Não é uma
probabilidade ou garantia de generalização. `dataset_sha256` identifica a matriz
preparada; não substitui guardar as amostras originais e a versão do código.

## Outros dados

`alembic_version` guarda apenas a revisão do esquema (`0003` atualmente). RLS está
ativo nas três tabelas. Não há tabela de notificações, garantia de entrega ou log
persistente de cada aviso; o roteiro/tabela PEAS documenta situações representativas.

Para exportar a base completa de um dispositivo:

```bash
cd backend
python -m app.export_dataset --device-id esp32-01 --output ../ml/data/historico.csv
```

Para reproduzir o corte do primeiro experimento de temperatura, acrescentar
`--max-id 489`. A pasta `ml/data/` fica fora do Git; entregar o CSV separadamente.
