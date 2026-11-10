# Matriz de atendimento ao trabalho — revisão 10/11/2026

Fonte: enunciado “Agentes, IoT e Aprendizado de Máquina”, IFSULDEMINAS Campus
Machado, Prof. Matheus Franco. Código implementado não equivale automaticamente a
validação de campo. Esta versão substitui o planejamento inicial desatualizado.

| Requisito | Implementação/evidência | Limite ou ação final |
|---|---|---|
| ESP com Wi-Fi e sensores | Firmware ESP32, DHT11 GPIO4 e solo GPIO34 | Anexar foto e versão física do sensor |
| Aquisição periódica, horário e unidades | Leitura a cada 3 s; envio a cada 30 s; UTC por NTP; schema validado | Rede precisa liberar internet/NTP |
| Envio automático à nuvem | HTTPS direto, TLS validado; HTTP 201 observado na placa | Sem fila persistente; não há coletor obrigatório |
| Histórico persistente | Supabase/PostgreSQL, migrações 0001–0003 e RLS | CSV da base anexado separadamente |
| Dashboard atual, gráfico e período | React/Vercel com cartões, SVG, filtros e CSV | Publicar versão atual; máximo 1.000 pontos por consulta |
| Estado/falhas | Sem dados, atraso, erro HTTP, descarte de inválidos e logs | Falhas não são registradas em tabela própria |
| ML com dados do projeto | Random Forest de temperatura, 489 leituras reais; relatório JSON salvo | Resultado preliminar, não supera baseline |
| Resultado do modelo no painel | Endpoint por alvo e seção de temperatura 5 min | Publicar backend/frontend para demonstrar a nova seção |
| Comparação com regra/baseline | MAE/RMSE versus persistência, mesma divisão temporal | Não alegar melhoria onde não houve |
| Aviso/ação útil | Condição atual por regra; avisos ML e notificação quando modelo elegível | Irrigação preditiva local ainda não validada |
| PEAS, percepções/ações e sequência | `docs/relatorio-tecnico.md` | Equipe deve revisar e assinar |
| Código-fonte | Firmware, API, React, treino automático e scripts de exportação | Não incluir segredos |
| Base demonstrável e descrição de campos | `ml/data/esp32-temperature-training.csv` e dicionário | Base fora do Git; entregar separadamente |
| Relatório técnico | `docs/relatorio-tecnico.md`, métricas e limitações reais | Preencher autor/turma e acrescentar foto/evidências finais |
| Apresentação | `docs/apresentacao.md`, sequência e respostas ao professor | Fazer a demonstração física, sem forjar alertas |

## Interpretação do atendimento

A parte de implementação e a documentação foram preparadas, incluindo treino
com dados reais. O enunciado exige comparar o ML ao baseline; não estabelece uma
margem mínima de melhoria. Os resultados negativos devem ser apresentados e
justificados, não removidos ou substituídos por métricas inventadas.

A previsão de temperatura é um experimento próprio permitido pelo enunciado e
não é uma recomendação de irrigação. A previsão de solo continua como objetivo
operacional, condicionado a dados e calibração. O modelo externo complementa o
estudo; não substitui o experimento com a placa.

A conclusão acadêmica depende da revisão do professor e da demonstração/entrega
pela equipe. Não é possível garantir aprovação, eficácia agronômica ou validações
físicas que ainda não foram realizadas.

## Documentos finais

- Relatório: `docs/relatorio-tecnico.md`.
- Dicionário: `docs/dicionario-dados.md`.
- Apresentação: `docs/apresentacao.md`.
- Treino real: `ml/reports/esp32-temperature.json`.
- Experimento externo: `ml/EXTERNAL_DATASET.md` e `ml/reports/external-soil.json`.
- Operação: `firmware/README.md`, `docs/deploy-render.md`, `dashboard/README.md`.
- Avisos: `docs/avisos-irrigacao.md`.

## Encerramento prático

1. Publicar as mudanças de API e React e conferir o modelo de temperatura no site.
2. Entregar CSV e fonte do experimento com hash correspondente.
3. Preencher equipe/turma e anexar fotografia do circuito.
4. Executar o roteiro de demonstração real e registrar resultados observados.
5. Informar que o ML ainda é experimental e que os avisos atuais por regra são
   distintos das recomendações preditivas de irrigação.
