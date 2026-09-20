# Configuração da conexão com o Instagram

Feito uma vez. Leva de 10 a 20 minutos. Ao final você terá um token de
longa duração (60 dias) para colocar em `.claude/skills/instagram/.env`.

## Pré-requisitos

- Conta do Instagram do tipo **Profissional** (Business ou Creator).
  Configurações → Tipo de conta → Mudar para conta profissional.
- Uma **Página do Facebook** vinculada a essa conta do Instagram
  (só para o caminho A). Instagram → Configurações → Central de contas.

Existem dois caminhos. O caminho A é o mais completo e o padrão da skill.

## Caminho A: Instagram API com Facebook Login (padrão)

1. Acesse https://developers.facebook.com/apps e clique em **Criar app**.
   Tipo: **Empresa** (Business). Dê um nome, por exemplo `github-slideshow`.
2. No painel do app, adicione o produto **Instagram** → *API setup with
   Facebook login*. Adicione também **Facebook Login for Business** se pedido.
3. Anote em *Configurações do app → Básico* o **ID do app** e a **Chave
   secreta do app**. Vão para `IG_APP_ID` e `IG_APP_SECRET`.
4. Gere um token de teste no **Explorador da Graph API**
   (https://developers.facebook.com/tools/explorer):
   - Selecione o seu app no canto superior direito.
   - Em *Permissões*, marque:
     `instagram_basic`, `instagram_content_publish`,
     `instagram_manage_insights`, `instagram_manage_comments`,
     `pages_show_list`, `pages_read_engagement`, `business_management`.
   - Clique em **Generate Access Token** e autorize a Página e a conta do
     Instagram. Esse token dura cerca de 1 hora.
5. Troque por um token de 60 dias:

   ```bash
   IG_APP_ID=... IG_APP_SECRET=... \
   python3 .claude/skills/instagram/scripts/ig.py token-exchange --token <token_curto>
   ```

   Copie o `access_token` da resposta para `IG_ACCESS_TOKEN` no `.env`.
6. Teste:

   ```bash
   python3 .claude/skills/instagram/scripts/ig.py accounts
   python3 .claude/skills/instagram/scripts/ig.py me
   ```

   Se `accounts` mostrar mais de uma conta, coloque o `id` desejado em
   `IG_USER_ID`.

Enquanto o app estiver em **modo de desenvolvimento**, só as contas listadas
em *Funções do app* (administradores, desenvolvedores, testadores) conseguem
usar o token. Para uso próprio isso basta; não é preciso enviar o app para
revisão da Meta.

## Caminho B: Instagram API com Instagram Login

Não precisa de Página do Facebook, mas não expõe algumas métricas e o
token só funciona na conta que fez login.

1. Crie o app como acima e adicione o produto **Instagram** → *API setup
   with Instagram business login*.
2. Em *Business login settings*, gere o token pelo botão de teste ou faça o
   fluxo OAuth com os escopos `instagram_business_basic`,
   `instagram_business_content_publish`,
   `instagram_business_manage_insights`,
   `instagram_business_manage_comments`.
3. No `.env`, defina `IG_GRAPH_HOST=graph.instagram.com` e `IG_APP_SECRET`.
4. Troque e renove tokens com:

   ```bash
   python3 .claude/skills/instagram/scripts/ig.py token-exchange --token <token_curto>
   python3 .claude/skills/instagram/scripts/ig.py token-refresh   # antes dos 60 dias
   ```

## Renovação

Tokens de longa duração expiram em 60 dias. `token-debug` mostra a data.
No caminho A gere um token curto novo no Explorador e repita o
`token-exchange`. No caminho B basta `token-refresh` enquanto o token ainda
estiver válido.

## Segurança

- `.env` está no `.gitignore`. Nunca faça commit do token.
- O token dá poder de publicar na sua conta. Se vazar, revogue em
  https://www.facebook.com/settings?tab=business_tools ou regenerando a
  chave secreta do app.
