# Apresentação e roteiro de demonstração

## Conteúdo sugerido (8–10 minutos)

1. **Problema e agente (1 min):** observar o ambiente e apoiar a inspeção de
   irrigação. Mostrar PEAS e esclarecer que a ação é digital, sem bomba automática.
2. **Circuito e sensores (1 min):** mostrar ESP32, GPIO4 e GPIO34, foto e valores
   reais. Explicar a diferença entre ADC e percentual estimado do solo.
3. **Arquitetura (1 min):** ESP32 → HTTPS Render → Supabase → React/Vercel. Mostrar
   que o computador não executa coletor e que mudar Wi-Fi não muda a URL da API.
4. **Histórico e dashboard (2 min):** demonstrar HTTP 201 no Serial, uma nova linha
   no banco, atualização dos cartões, gráficos, filtro e exportação CSV.
5. **ML real e avaliação (2 min):** explicar Random Forest, atributos, alvo futuro,
   divisão temporal e baseline. Mostrar modelo de temperatura com dados da ESP32,
   métricas reais e previsão experimental. Não ocultar que perdeu para persistência.
6. **Aviso, falha e conclusões (1–2 min):** mostrar condição por regra identificada,
   fluxo de alertas ML condicionado à qualidade, ausência de dados e limitações.

## Preparação

- Preencher nomes/turma e anexar foto/esquema final do circuito.
- Publicar os novos backend/frontend; o modelo real já está salvo no banco.
- Ter a chave da API disponível sem projetá-la na apresentação.
- Alimentar a placa e conferir HTTP 201; deixar a página aberta/atualização ativada.
- Separar base exportada, relatório técnico, relatórios JSON e fontes.
- Para notificações, conceder permissão; o navegador pode não notificar em todos os
  dispositivos. Não forjar um aviso ML real se o modelo estiver experimental.

## Demonstração real

1. Conferir que o coletor Python está desligado.
2. Mostrar o Serial da ESP32 com HTTP 201 e horário UTC.
3. Abrir a dashboard e indicar a conversão para horário de Brasília.
4. Esperar uma amostra nova e comparar com a tabela `measurements` no Supabase.
5. Aplicar um intervalo de tempo e exportar CSV.
6. Mostrar a previsão de temperatura e o MAE versus persistência; explicar o alvo
   de 5 min. Separar da previsão de solo de 30 min e do experimento público.
7. Mostrar o aviso atual por regra. Dizer explicitamente que não é ML nem uma
   confirmação agronômica de irrigação.
8. Para testar ausência de comunicação, desligar a placa e aguardar mais de 5 min.
   O painel deverá indicar atraso. Depois religar e conferir novos HTTP 201.
9. Mostrar um cenário controlado dos testes de aviso/notificação apenas como teste
   de software, identificado como simulado, caso não haja alerta ML real válido.

## Respostas às questões do professor

- **Leitura física → decisão:** sensores produzem valores; firmware valida, API
  registra e o backend compara condição/regressão futura com limites declarados.
- **Por que histórico:** comprova evolução, permite alvo futuro, avaliação e auditoria.
- **Padrões encontrados:** variação de temperatura e umidade e períodos de solo
  constante, com interrupções de coleta. Usar gráficos reais para exemplos.
- **Escolha e avaliação:** Random Forest já estudado em aula, leve para backend;
  MAE/RMSE em teste posterior ao treino e comparação com persistência.
- **Utilidade do aviso:** pode antecipar inspeção quando validado; nos experimentos
  atuais, o modelo perdeu para o baseline e ainda não justifica irrigação automática.
- **Mais autonomia/eficiência:** envio direto já implementado; próximas melhorias
  são coleta representativa, energia estável, fila local, autenticação por dispositivo
  e canal persistente de notificações.

## Evidências que não podem ser inventadas

Fotografia física, eficácia agronômica, disponibilidade contínua, resultados de
novos ciclos de campo e entrega real de notificações devem ser obtidos na prática.
O relatório já diferencia resultados reais, externos e testes controlados.
