# Carrossel — Mercado Livre Experience 2026 (Ponto de Decisão #002)

Paleta **Evidência** (extraída de `camila-lonaro-portfolio-evidencia.pdf`):

| Papel | Hex |
|---|---|
| Marfim (fundo) | `#F2EFE8` |
| Preto (títulos) | `#1A1A1A` |
| Ouro (destaques, itálico) | `#B08D45` |
| Cinza texto | `#3A3A3A` |
| Ouro apagado (rodapé) | `#9A927F` |

Tipografia: Bodoni Moda (títulos e frases), Manrope (kickers e rodapé, caixa alta espaçada).

Arquivos `01-capa.jpg` … `06-mascote.jpg` são 1080×1350 (4:5), JPEG q95, renderizados em 2× e reduzidos com LANCZOS.
Os `.html` são os templates usados para gerar as imagens (fotos originais não estão no repositório).

Publicar (localmente, com o skill `instagram`):

```
python3 .claude/skills/instagram/scripts/ig.py publish-carousel \
  --urls <url-01> <url-02> <url-03> <url-04> <url-05> <url-06> \
  --caption-file caption.txt
```
