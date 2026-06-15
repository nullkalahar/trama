# Trama v2.1.32

Tema: multipart/streaming robusto para upload grande.

Entregas:
- parse multipart sem depender de `payload` inteiro em memória
- arquivo grande segue em tempfile e entra na requisição com:
  - `streaming`
  - `caminho_temporario`
  - `bytes = nulo` quando o conteúdo foi mantido fora da memória

Semântica:
- contratos e validações de formulário/arquivo continuam compatíveis com a fachada anterior
