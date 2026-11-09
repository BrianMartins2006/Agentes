# Deploy da API na Render

O banco fica no Supabase; a Render executa o FastAPI e o treino automático.
O React será publicado separadamente na Vercel. Não é necessário Docker para
esse deploy; o `compose.yaml` serve somente ao desenvolvimento local.

## Criar o serviço

O `render.yaml` na raiz prepara um Blueprint, sem credenciais versionadas.
Na Render, selecione **New > Blueprint**, conecte o repositório
`BrianMartins2006/Agentes` e escolha a branch `main`. Confira o serviço antes de
criar e informe os valores secretos solicitados:

- `DATABASE_URL`: o mesmo valor do `.env` que já funciona com o Supabase, usando
  `postgresql+psycopg://`, Session Pooler porta 5432 e SSL.
- `INGEST_API_KEY`: o valor configurado no `.env`, usado pelo coletor e pelo operador.

Alternativamente, crie **New > Web Service** com os seguintes campos:

| Campo | Valor |
|---|---|
| Branch | `main` |
| Runtime | Python |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Plano inicial | Free, para demonstração |

No modo manual, configure também `ML_AUTO_TRAIN_ENABLED=true` e
`CORS_ORIGINS=[]` inicialmente. Depois do deploy da Vercel, atualize CORS para a
origem exata, como `["https://SEU-FRONT.vercel.app"]`, sem barra final.
Para testar React local contra a API hospedada, inclua `http://127.0.0.1:5173`.

As migrações rodam antes do servidor HTTP. A primeira versão cria o esquema e a
0003 habilita RLS nas três tabelas públicas. Sem políticas públicas, acessos como
`anon`/`authenticated` ficam bloqueados pelo RLS; o backend usa o proprietário das
tabelas, cujo acesso não é sujeito ao RLS. Não fornecer essa conexão ao navegador.
Se mudar o usuário do banco, suas permissões precisam ser avaliadas explicitamente.

## Validar

Após concluir, a Render fornece `https://SEU-SERVICO.onrender.com`.

1. Abra `/health`: deve retornar `{"status":"ok"}`. É teste do processo, não do banco.
2. Abra `/docs` e use **Authorize** com a chave para consultar `/api/v1/measurements`.
3. Confira os logs de inicialização e da verificação do treino automático.
4. No coletor local, ajuste `API_BASE_URL` para a URL HTTPS e reinicie-o.
5. Depois configure `VITE_API_URL` na Vercel e libere sua origem no CORS.

A raiz da API pode mostrar apenas informações do serviço: o React será servido
pela Vercel, pois seu build não é produzido no deploy Python da Render.

O Free pode suspender o processo por inatividade: o treino também para e retoma
quando a instância volta. Para execução contínua, avaliar plano sempre ativo.
Não foram criados serviços pagos ou agendamentos por esse arquivo.

Referências: [FastAPI na Render](https://render.com/docs/deploy-fastapi),
[Blueprints](https://render.com/docs/blueprint-spec) e
[Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).
