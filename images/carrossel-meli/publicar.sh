#!/usr/bin/env bash
# Publica o carrossel do Mercado Livre Experience 2026 no @camilalonaro.
# Uso:  bash images/carrossel-meli/publicar.sh            (publica)
#       bash images/carrossel-meli/publicar.sh --dry-run  (só cria os containers, não publica)
set -euo pipefail
cd "$(dirname "$0")/../.."
BASE="https://raw.githubusercontent.com/CamilaLonaro/github-slideshow/1ba8b670f60a8dc9dce71e36c3316ade717c990f/images/carrossel-meli"
python3 .claude/skills/instagram/scripts/ig.py publish-carousel "$@" \
  --caption "$(cat images/carrossel-meli/caption.txt)" \
  "$BASE/01-capa.jpg" "$BASE/02-boasvindas.jpg" "$BASE/03-prazo.jpg" \
  "$BASE/04-mercadopago.jpg" "$BASE/05-pausa.jpg" "$BASE/06-mascote.jpg"
