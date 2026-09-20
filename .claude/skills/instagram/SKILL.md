---
name: instagram
description: Publica no Instagram (imagem, Reel, carrossel, story), lê métricas de posts e da conta, gerencia comentários e renova tokens usando a Instagram Graph API da Meta. Use quando o usuário pedir para postar, agendar conteúdo, ver alcance/likes/seguidores, responder comentários ou verificar o token do Instagram.
---

# Instagram (Graph API)

Esta skill fala com a **Instagram Graph API** da Meta através do script
`scripts/ig.py` (Python 3, só biblioteca padrão). Não há conector MCP oficial
do Instagram, então toda a conexão passa por um token de acesso que o usuário
gera uma vez no Meta for Developers.

## Antes de qualquer comando

1. Confira se as credenciais existem: `IG_ACCESS_TOKEN` no ambiente ou em
   `.claude/skills/instagram/.env` (copie de `.env.example`). Nunca grave o
   token em arquivos versionados nem o imprima no chat.
2. Se não houver token, siga `reference/setup.md` com o usuário e pare por aí.
3. Valide a conexão com `python3 .claude/skills/instagram/scripts/ig.py me`.
   Se falhar com `code=190`, o token expirou: use `token-exchange` ou
   `token-refresh` (ver abaixo).

Todos os comandos abaixo assumem o prefixo
`python3 .claude/skills/instagram/scripts/ig.py`.

## Leitura e métricas

| Objetivo | Comando |
|---|---|
| Perfil, seguidores, nº de posts | `me` |
| Páginas/contas que o token enxerga | `accounts` |
| Últimos posts | `media --limit 25` |
| Detalhes de um post | `media-get <media_id>` |
| Métricas de um post | `media-insights <media_id>` |
| Métricas da conta (série + totais) | `account-insights --since 2026-09-01 --until 2026-09-20` |
| Resumo pronto (conta + últimos N posts) | `report --limit 10` |
| Cota de publicação (100 posts/24h) | `limit` |

Notas:
- `media-insights` escolhe as métricas certas pelo tipo de mídia. Passe
  `--metrics views,reach,saved` para escolher à mão.
- `account-insights` sem `--metrics` traz `reach` e `follower_count` por dia
  mais os totais (`views`, `accounts_engaged`, `likes`, `saves`, etc.).
  Períodos maiores que 30 dias devem ser quebrados em janelas.
- Métricas de conta exigem pelo menos 100 seguidores em alguns casos; a API
  devolve erro claro quando isso acontece. Repasse a mensagem ao usuário.

## Publicação

Toda mídia precisa estar em uma **URL pública** que os servidores da Meta
consigam baixar. Neste repositório (GitHub Pages) uma imagem commitada em
`images/` fica acessível em `https://<usuario>.github.io/github-slideshow/images/<arquivo>`
depois do deploy. Alternativas: Google Drive com link direto, S3, Cloudinary.

Requisitos da Meta:
- Imagem: JPEG, até 8 MB, proporção entre 4:5 e 1.91:1.
- Reel: MP4/MOV, 9:16, 3 s a 15 min, até 1 GB.
- Carrossel: 2 a 10 itens, imagens ou vídeos.
- Story: imagem ou vídeo, some após 24 h.

| Objetivo | Comando |
|---|---|
| Imagem única | `publish-image --image-url URL --caption "texto"` |
| Reel | `publish-video --video-url URL --caption "texto"` |
| Carrossel | `publish-carousel --caption "texto" URL1 URL2 URL3` |
| Story | `publish-story --image-url URL` ou `--video-url URL` |
| Só preparar, sem publicar | acrescente `--dry-run`; publique depois com `publish-container <id>` |
| Ver processamento de vídeo | `container-status <container_id>` |
| Apagar post | `delete <media_id> --yes` |

Regras para o agente:
- **Confirme com o usuário** legenda e mídia antes de publicar. Publicar é
  irreversível do ponto de vista de alcance; use `--dry-run` quando houver
  dúvida e mostre o container id.
- Nunca apague um post sem pedido explícito.
- Depois de publicar, devolva ao usuário o `permalink` que o script imprime.
- Hashtags e menções vão dentro de `--caption`. Quebras de linha funcionam
  com `$'linha1\nlinha2'` no bash.

## Comentários

| Objetivo | Comando |
|---|---|
| Listar comentários | `comments <media_id>` |
| Responder | `reply <comment_id> "mensagem"` |
| Ocultar / reexibir | `hide-comment <comment_id>` / `--unhide` |

## Tokens

| Situação | Comando |
|---|---|
| Ver validade e escopos | `token-debug` |
| Token curto (1 h) → longo (60 dias) | `token-exchange --token <curto>` |
| Renovar token longo (só Instagram Login) | `token-refresh` |

O resultado de `token-exchange` / `token-refresh` contém `access_token`;
oriente o usuário a colocar o novo valor no `.env`. Não cole o token no chat.

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `IG_ACCESS_TOKEN` | sim | Token de usuário com os escopos da seção Setup |
| `IG_USER_ID` | não | ID da conta profissional; descoberto automaticamente se vazio |
| `IG_APP_ID` / `IG_APP_SECRET` | para tokens | Credenciais do app na Meta |
| `IG_GRAPH_HOST` | não | `graph.facebook.com` (padrão, login via Facebook) ou `graph.instagram.com` (login via Instagram) |
| `IG_API_VERSION` | não | Padrão `v23.0` |

## Erros comuns

- `code=190`: token inválido ou expirado → renovar.
- `code=10` / `(#10)`: permissão faltando no token → refazer login com os escopos.
- `code=100` com "media_type" ou "image_url": URL não pública ou formato errado.
- `code=9` / `(#9)`: cota de 100 publicações em 24 h atingida → `limit`.
- `code=4`: limite de chamadas da API → esperar e tentar de novo.
