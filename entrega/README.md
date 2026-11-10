# Pacote para entrega acadêmica

O ZIP inclui código sem segredos, relatório técnico, roteiro de apresentação,
dicionário, relatórios de ML e CSV real de 489 amostras. A base foi incluída no ZIP
para o professor, mas continua fora do Git. Não há `.env`, `secrets.h`, binários,
node_modules ou configuração pessoal.

Antes de entregar:

1. Preencher nomes completos/turma no relatório.
2. Anexar foto do protótipo e confirmar tensões/fiação reais.
3. Publicar backend/frontend e demonstrar a nova previsão de temperatura.
4. Explicar resultados experimentais e a ausência de validação de irrigação por ML.
5. Executar a demonstração real e registrar ausência de dados/reconexão.

O snapshot de temperatura pode ser reproduzido no banco original:

```bash
cd backend
python -m app.train_model --device-id esp32-01 --target temperature_c --max-id 489 --as-of 2026-11-10T11:21:00+00:00 --report ../ml/reports/reproducao.json
```

O professor pode inspecionar o CSV e o código sem acessar o banco remoto. Para
executar o projeto em outro ambiente, configurar segredos locais próprios com os
arquivos de exemplo; nunca incluir as credenciais reais da equipe na entrega.
