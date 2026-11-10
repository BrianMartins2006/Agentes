# Avisos de irrigação por previsão do modelo

O sistema interpreta a previsão do Random Forest da própria placa para orientar o
produtor. O modelo aprende a leitura futura; uma regra de decisão compara essa
previsão ao limite de solo. A regra não é apresentada como aprendizado de máquina.

## Estados no painel

- **Solo atual e futuro abaixo do limite:** recomendar inspeção e planejamento da
  irrigação conforme a cultura. Produz aviso e pode notificar o navegador.
- **Solo atual acima, previsão abaixo:** aviso antecipado de risco de secagem, com
  horário-alvo. Pode notificar o navegador.
- **Solo atual abaixo, previsão de recuperação:** solicitar inspeção; sem aviso
  automático de irrigação baseado somente na leitura atual.
- **Previsão acima do limite:** sem aviso preditivo de solo seco. Isso não certifica
  que todas as condições da cultura estejam adequadas.
- **Modelo ausente, experimental, externo ou dados atrasados:** avaliação
  indisponível. Não emite recomendação automática nem notificação de irrigação.

A umidade do ar já participa do modelo como atributo. Quando baixa, aparece como
contexto adicional no aviso; ar seco sozinho não determina necessidade de rega.
Não há irrigação automática, controle de bomba ou estimativa do volume de água.

## Limites configuráveis no backend

```dotenv
IRRIGATION_SOIL_THRESHOLD_PCT=30
IRRIGATION_AIR_THRESHOLD_PCT=40
```

São referências de demonstração, não recomendações universais para qualquer
cultura. Os percentuais do solo vêm da calibração do firmware (4095 seco / 2901
molhado). Validar esses pontos e adequar os limites ao solo, à cultura e ao manejo.
O percentual do sensor local não é intercambiável com o percentual do dataset de
campo usado no experimento externo.

## Notificações do navegador

No painel, clicar em **Ativar avisos do navegador** e conceder permissão. O pedido
só aparece por iniciativa do operador. A página precisa permanecer aberta: não é
push em segundo plano e não funciona com o navegador fechado. Enquanto a aba está
oculta, a consulta periódica atual fica pausada; ao voltar, a próxima consulta
atualiza o aviso. Restrições do navegador/SO podem impedir notificações; o aviso
continua visível no painel.

Notificações iguais para o mesmo dispositivo são limitadas a uma a cada 30 minutos
na mesma sessão. A mudança de nível pode gerar novo aviso; normalização seguida de
um novo episódio também. O estado de deduplicação usa `sessionStorage` sem senha ou
chave de acesso. Não existe deduplicação entre computadores/abas diferentes.
Previsões com mais de cinco minutos não geram notificações.

Nenhuma mensagem WhatsApp/e-mail é enviada. Não há registro persistente ou
comprovante de entrega dos avisos nesta versão. Esses são próximos passos caso a
notificação deva chegar ao produtor mesmo sem estar acompanhando a dashboard.

## Situação real do projeto

A interface e a decisão foram testadas com casos controlados. Para funcionar no
campo, é necessário que o modelo da placa exista, tenha MAE menor que o baseline
no teste e receba leituras válidas recentes. Isso é uma condição técnica inicial,
não uma prova de validação agronômica.

Se o solo continuar fixo em 4095, não haverá treino confiável dessa variável. O
experimento externo já treinado não substitui essa validação e não aciona avisos
para a ESP32. Corrigir/verificar o sensor e coletar diferentes condições reais é
necessário para concluir a demonstração preditiva do sistema.

Para publicar a funcionalidade, subir backend e frontend atualizados. Não há nova
migração de banco; `GET /api/v1/predictions` passou a incluir o objeto `irrigation`.
O firmware não precisa ser regravado para essa mudança.
