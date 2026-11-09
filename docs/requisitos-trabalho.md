# Plano de atendimento — Agentes, IoT e Aprendizado de Máquina

Fonte: enunciado fornecido pelo usuário nesta conversa. Este documento distingue
o que existe do que ainda precisa ser implementado e demonstrado com dados reais.

## Problema e arquitetura

Monitorar o ambiente e o solo para antecipar ressecamento e orientar uma inspeção
ou rega. A ESP32 é admitida pelo enunciado, que aceita outras placas ESP com Wi-Fi.

Fluxo atual implementado, ainda sem validação integrada de hardware e nuvem:

ESP32 → HTML por Wi-Fi → coletor local → FastAPI → PostgreSQL.

Destino planejado: FastAPI na Render e PostgreSQL no Supabase. A dashboard consulta os dados e a previsão pelo backend. O treino salva o modelo
e as métricas no banco; ainda não há treino com dados reais. Credenciais do banco ficam no backend.

O coletor precisa de um computador ou Raspberry Pi ligado na rede da placa.
Um agendador em nuvem não acessa diretamente o IP privado da ESP32. O envio
direto da placa para a API eliminaria esse intermediário, mas exige alteração de
firmware e permanece dependente de autorização explícita. Confirmar com o professor
se o uso de gateway atende à exigência de a placa enviar automaticamente à nuvem.

## Automação: responsabilidades distintas

- Coleta periódica: manter o coletor em serviço, iniciando no boot e reiniciando
  após falhas. Proposta para a coleta de campo: uma amostra por minuto; ajustar
  `POLL_SECONDS` após avaliar as variações reais. O padrão atual continua 10 s.
- Verificação diária: consultar dados reais, contar amostras das últimas 24 h,
  verificar a última comunicação e registrar um resumo ou falha. Horário proposto:
  09:00 America/Sao_Paulo, equivalente a `0 12 * * *` em um cron que usa UTC.
- Análise do modelo: atualizar a previsão quando chegar uma amostra válida;
  avaliar retreinamento quando houver histórico novo suficiente.

Uma coleta por dia não foi proibida pelo enunciado, mas produz poucas amostras e
dificulta demonstrar variações, identificar falhas rapidamente e avaliar ML.
A verificação diária não substitui a coleta periódica nem o monitoramento de
atraso na dashboard. Nenhum agendamento foi ativado nesta etapa.

Consultas agendadas não garantem a disponibilidade de planos gratuitos nem a
reativação de banco pausado. Não inserir medições fictícias para simular atividade.

## Matriz de requisitos e evidências

| Requisito | Situação atual | Trabalho e evidência necessários |
|---|---|---|
| ESP com Wi-Fi e sensores | Código fornecido; funcionamento informado pelo usuário | Foto do circuito, identificação dos pinos e demonstração real |
| Aquisição periódica e horário | Coletor contínuo implementado; horário UTC do computador | Validar relógio, intervalo e amostras reais; registrar origem do horário |
| Unidades e identificação | Campos `temperature_c`, `air_humidity_pct`, `soil_raw`, `device_id` | Dicionário de dados e calibração versionada do solo |
| Leituras inválidas | Schema e parser rejeitam amostras inválidas | Persistir eventos de falha para exibição e diagnóstico |
| Envio automático HTTP/MQTT | Coletor envia HTTP à API | Configurar serviço automático, HTTPS e testar integração; validar gateway com professor |
| Histórico persistente | Modelo SQLAlchemy e migração Alembic | Criar Supabase, aplicar migração, comprovar dados após reinício e exportar base |
| Valores atuais e gráfico | Implementados na dashboard | Validar com hardware e banco reais |
| Filtros e intervalo | API e painel têm dispositivo, início e fim | Interface limita a 1.000 pontos; ampliar paginação/agregação para histórico extenso |
| Estado e falhas | Painel mostra sem dados, atualizado, atrasado e erro; consulta diária SQL pronta | Ativar agendamento; persistir eventos de falha e validar em campo |
| ML treinado com dados coletados | Pipeline, treino e avaliação implementados; sem treino de campo | Coletar base real, executar treino e analisar métricas versus baseline |
| Resultado do ML no painel | API e interface implementadas | Demonstrar previsão real, horizonte, versão e comparação ao baseline |
| Aviso ou ação útil | Painel da placa já tem avisos por limiar | Integrar aviso preditivo e registrar percepção, decisão e ação |
| PEAS e sequência | Proposta neste documento | Validar escolhas e incorporar ao relatório |
| Relatório e apresentação | Pendente | Relatório técnico, resultados reais e roteiro de demonstração |

## PEAS proposto

| Elemento | Definição |
|---|---|
| Desempenho | MAE da previsão versus baseline, taxa de amostras válidas, atraso de comunicação e utilidade dos avisos |
| Ambiente | Vaso/canteiro monitorado, condições ambientais e rede Wi-Fi |
| Atuadores | Avisos digitais no painel; nenhuma irrigação automática nesta proposta |
| Sensores | DHT11: temperatura e umidade do ar; sensor no GPIO34: leitura bruta relacionada à umidade do solo |

## Percepções, decisões e ações

| Percepção/condição | Decisão | Ação, aviso ou previsão |
|---|---|---|
| Amostra válida | Incorporar ao histórico | Atualizar gráfico e executar inferência quando houver modelo |
| DHT11 retorna erro | Não usar a amostra no modelo | Registrar evento e indicar falha de leitura |
| Última amostra ultrapassa o atraso tolerado | Estado atrasado; origem da falha ainda não determinada | Mostrar última comunicação e solicitar verificação de placa, coletor ou rede |
| Solo abaixo de 30% pela calibração vigente | Regra simples de solo seco | Aviso por limiar, identificado como regra e não como ML |
| Modelo prevê solo abaixo de 30% em 30 min | Possível ressecamento futuro | Aviso antecipado para inspeção; não acionar irrigação automaticamente |
| Histórico insuficiente ou modelo ausente | Não inferir | Exibir “modelo ainda indisponível”, sem resultado inventado |

O limiar de atraso deve ser configurável a partir do intervalo real de coleta.
Não atribuir automaticamente falta de dados a uma falha específica do sensor.

## Experimento de ML proposto

Objetivo inicial: prever umidade do solo em 30 minutos. A viabilidade desse
horizonte depende de variação suficiente no histórico; avaliar com os dados reais.

1. Registrar calibração por dispositivo e validade temporal (informado no firmware:
   seco 4095, molhado 2901). Converter para percentual de modo reprodutível.
2. Coletar vários ciclos reais de secagem/rega, registrando eventos e lacunas.
   Quantidade de linhas sozinha não comprova suficiência de dados.
3. Criar atributos apenas de dados disponíveis no instante da previsão:
   temperatura, umidade do ar, solo atual, valores anteriores e tendência passada.
4. Construir o alvo no horizonte escolhido; não interpolar por grandes lacunas e
   não misturar dispositivos/calibrações sem tratamento explícito.
5. Treinar Random Forest Regressor, conforme o conteúdo estudado em aula. Fazer divisão
   cronológica em treino, validação e teste; descartar da fronteira exemplos cujo
   alvo avance para a partição seguinte. Ajustar transformações só no treino.
6. Comparar MAE e RMSE com baseline de persistência: “o valor futuro será igual
   ao último valor conhecido”. Usar exatamente o mesmo conjunto de teste.
7. Versionar dataset, atributos, parâmetros, modelo e métricas. Se o modelo não
   superar o baseline, apresentar o resultado honestamente e discutir limitações.
8. Expor inferência na API e mostrar previsão, instante, horizonte e aviso no painel.
   Não apresentar probabilidade/confiança sem método de estimação e avaliação.

Limiares fixos não substituem este experimento. Dados sintéticos podem testar a
interface, mas devem ser identificados e não apresentados como resultados de campo.

## Ordem de implementação

1. Banco Supabase + configuração Render + teste real de envio e persistência.
2. Serviço local automático do coletor, registro de falhas e verificação diária.
3. Dashboard com atuais, histórico, filtros e estado; iniciar coleta de campo.
4. Calibração versionada, dataset e experimento ML comparado ao baseline.
5. Inferência e avisos no painel, registro de decisões e avaliação integrada.
6. Relatório, base exportada e apresentação com demonstração reproduzível.

Critério de conclusão: comprovar cada linha da matriz com implementação e evidência
real. O projeto atual ainda não atende integralmente ao enunciado.

## Entregáveis finais

- Protótipo e esquema do circuito, com alimentação e pinos documentados.
- Código do firmware autorizado, coletor, API, dashboard e ML, sem credenciais.
- Base histórica exportável e dicionário de campos/unidades/calibração.
- Dashboard com série real e pelo menos uma inferência do modelo treinado.
- Relatório: problema, PEAS, fluxo, tratamento de dados, método, métricas,
  comparação ao baseline, resultados, limitações e melhorias.
- Demonstração: nova leitura → banco → gráfico → previsão/aviso, incluindo teste
  de ausência de comunicação e explicação da recuperação.

## Referências de hospedagem

- [Supabase: conexão PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase: pausa por baixa atividade](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Render: Cron Jobs, horários em UTC e cobrança](https://render.com/docs/cronjobs)
- [Render: limites dos serviços gratuitos](https://render.com/docs/free)

## Atualização de implementação

Dashboard e pipeline Random Forest foram implementados, com testes automatizados e QA de
interface usando dados simulados. Isso valida o software, mas não comprova eficácia
preditiva em campo. O treino usa alvo bruto do solo; o percentual é uma conversão
informativa pela calibração do firmware. Os comandos estão em `ml/README.md`.


## React/Vercel e treino automático

A interface foi migrada para React/Vite e preparada para Vercel; a API permanece
na Render e usa CORS com origens explícitas. O treinamento automático roda no
backend durante a execução da API, com intervalo, cooldown e mínimo de novas
amostras configuráveis. Sua execução é suspensa se a instância de hospedagem
estiver parada. Coleta automática da placa, deploy e avaliação de campo continuam
pendentes; não confundir automação do treino com conclusão desses itens.
