# Dashboard React + Vite

Frontend independente para hospedar na Vercel, consumindo a API FastAPI na Render.
Mantém cartões, gráficos SVG, filtros, exportação CSV, estado da comunicação e
previsão do Random Forest. Não há dados demonstrativos embutidos.

## Desenvolvimento local

Requer Node 22.12+ e API em execução:

```bash
cd dashboard
cp .env.example .env
npm ci
npm run dev
```

Abra http://127.0.0.1:5173/. `VITE_API_URL` aponta para a API, por padrão
`http://127.0.0.1:8000`. Reinicie o Vite após mudar o `.env`.

## Vercel

Importe o repositório e configure:

- Root Directory: `dashboard`
- Framework: Vite
- Install: `npm ci`
- Build: `npm run build`
- Output: `dist`
- Variável: `VITE_API_URL=https://SUA-API.onrender.com`

`vercel.json` e o lockfile estão preparados. O projeto ainda não foi publicado.
A URL da API é pública. Nunca coloque a chave da API ou senha do banco em variáveis
`VITE_*`, pois seus valores são incorporados no JavaScript enviado ao navegador.

Na API Render, configure `CORS_ORIGINS` como uma lista JSON de origens permitidas:

```dotenv
CORS_ORIGINS=["https://SEU-FRONT.vercel.app"]
```

Use a origem exata sem barra final, incluindo domínio personalizado se houver.
URLs de preview diferentes precisam ser adicionadas explicitamente. Reinicie a API
ao mudar a configuração; na Vercel, gere novo deploy após mudar a URL de build.

## Acesso e comportamento

O operador abre a engrenagem ao lado do estado da conexão no topo para configurar
o dispositivo, a chave `X-API-Key` e a atualização automática. Os filtros de período
ficam junto do histórico. Cancelar ou pressionar Escape fecha a configuração sem
aplicar mudanças. A chave fica somente em memória enquanto a
página está aberta, sem localStorage/cookies. As requisições vão apenas para a API
configurada. Para produção use HTTPS. Esta é uma interface de operador: a chave
atual também permite ingestão; para vários usuários, implementar login e permissões
separadas. Senha do PostgreSQL fica exclusivamente no backend.

Atualiza medições e previsão a cada 30 segundos com a aba visível. Cada requisição
possui timeout; respostas de filtros anteriores são canceladas ao trocar a consulta.
Erros na previsão não ocultam as medições. O painel mostra se o treino automático
está ativado e a data do último modelo.

Consulta até 1.000 pontos do período, avisando quando chega ao limite. A tabela
mostra até 100 linhas e o CSV inclui todas as carregadas. Cartões e previsão usam
os dados mais recentes do dispositivo, independentemente do período filtrado.
Dados com mais de cinco minutos são indicados como atrasados; lacunas maiores que
cinco minutos interrompem as curvas. Datas usam o fuso do navegador.

## Build

```bash
npm run build
npm run preview
```

O resultado vai para `dashboard/dist/`, ignorado pelo Git. Opcionalmente, se esse
build existir ao iniciar o FastAPI, a API também serve a dashboard na raiz. Em
Vercel + Render, os serviços ficam separados e o build roda somente na Vercel.

Referências: [Vite na Vercel](https://vercel.com/docs/frameworks/frontend/vite)
e [CORS no FastAPI](https://fastapi.tiangolo.com/tutorial/cors/).


A seção **Experimento separado — Dataset público** consulta
`/api/v1/experiments/soil` e mostra o Random Forest treinado em dados públicos,
comparação com persistência e exemplos históricos, com fonte e licença. A seção
não apresenta esses dados como leituras ou previsões válidas para a ESP32.
