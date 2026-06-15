# Manual v2.1.31

## Fluxo de upload validado

```trama
sessao = armazenamento_iniciar_upload(storage, "docs/arquivo.txt", {
    "content_type": "text/plain",
    "validacao": {
        "mime_permitidos": ["text/plain"],
        "tamanho_maximo": 4096,
        "hash_sha256": "..."
    }
})
armazenamento_upload_escrever(storage, sessao["upload_id"], "conteudo")
final = armazenamento_upload_finalizar(storage, sessao["upload_id"])
```

Resultado:
- objeto final salvo
- metadados e políticas persistidos
