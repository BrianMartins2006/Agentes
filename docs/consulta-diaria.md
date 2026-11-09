# Consulta diária ao Supabase

Objetivo solicitado: consultar o banco automaticamente para manter atividade.
A tarefa faz uma consulta útil ao histórico real e informa se a coleta está atual.
Ela não garante que o Supabase manterá um projeto Free ativo: a documentação fala
em baixa atividade ao longo de sete dias, sem garantir uma exceção para uma
consulta diária. Um projeto já pausado precisa ser restaurado pelo procedimento
do provedor. Para disponibilidade sem pausa por inatividade, avaliar plano pago.

## Comando preparado

Com ambiente virtual ativo e dentro de `backend/`:

```bash
python -m app.daily_check --device-id esp32-01 --max-age-seconds 300
```

Saída JSON: conectividade do banco, dispositivo, número de amostras recebidas nas
últimas 24 horas, horário de chegada mais recente e estado de atualização. O limite
de 300 segundos é uma proposta para coleta frequente, não uma regra do trabalho.
A tarefa não insere ou modifica medições. Usa `received_at` para verificar chegada;
isso não comprova sincronização do relógio do sensor ou qualidade física da leitura.

Códigos de saída: 0 = banco acessível e dados atuais; 1 = erro na consulta;
2 = banco acessível, mas dados ausentes, atrasados ou horário inconsistente.
O agendador deve registrar inclusive saídas com erro para permitir diagnóstico.

## Agendar na Render

Configuração proposta, ainda não criada ou ativada:

| Campo | Valor |
|---|---|
| Tipo de serviço | Cron Job (possui cobrança própria) |
| Repositório | O repositório deste projeto, após publicação |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Command | `python -m app.daily_check --device-id esp32-01 --max-age-seconds 300` |
| Schedule | `0 12 * * *` — 09:00 em America/Sao_Paulo, atualmente UTC−3 |

Configurar `DATABASE_URL` com a URI do Session Pooler do Supabase, usando o driver
`postgresql+psycopg://` e SSL conforme as instruções de conexão do provedor. Não
copiar a senha para arquivos versionados. A configuração compartilhada atual
também exige `INGEST_API_KEY`; configurar a mesma variável secreta usada na API,
embora esta consulta SQL não faça chamadas HTTP. Não precisa de `ESP32_URL`.

A migração `alembic upgrade head` deve ter sido aplicada antes de executar o job.
O agendador executa uma vez e o processo termina; ele não depende de um loop dentro
da API. Usar a tela de execuções da Render para conferir a primeira consulta e as
seguintes. Os logs não são um arquivo de relatório histórico no banco.

Alternativa: executar o mesmo comando pelo cron de um computador/Raspberry Pi
sempre ligado, com ambiente virtual e diretório corretos. Nesse caso, não há job
Render, mas a execução depende da máquina e da conexão local.

## Relação com o trabalho acadêmico

Esta consulta diária não coleta dados novos da ESP32 nem substitui envio periódico,
dashboard ou ML. Para atender ao trabalho, manter coleta frequente, histórico real,
monitoramento de falhas e implementação das pendências na matriz de requisitos.

Referências: [Supabase: pausa de projetos](https://supabase.com/docs/guides/platform/free-project-pausing),
[conexão PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres)
e [Render: Cron Jobs](https://render.com/docs/cronjobs).
