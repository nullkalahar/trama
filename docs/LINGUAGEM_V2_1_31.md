# Trama v2.1.31

Tema: pipeline de upload formal no storage.

Entregas:
- upload em etapas: iniciar, escrever, finalizar
- validação de MIME, tamanho e hash SHA-256
- promoção temporário->definitivo
- integração com backend local e S3-compatível

Superfície pt-BR:
- `armazenamento_iniciar_upload`
- `armazenamento_upload_escrever`
- `armazenamento_upload_finalizar`
- `armazenamento_processar_upload`
- `armazenamento_promover`
