# Linguagem Trama v1.2

## Objetivo

Entregar suporte robusto para:

- uploads `multipart/form-data`;
- pipeline de mídia (compressão e processamento de imagem);
- abstração de storage (local e S3-compatível).

## 1. Multipart/form-data no runtime HTTP

A `requisicao` agora inclui:

- `requisicao["formulario"]` (alias: `requisicao["form"]`)
- `requisicao["arquivos"]` (alias: `requisicao["files"]`)

Cada arquivo enviado contém:

- `campo`
- `nome_arquivo`
- `content_type`
- `tamanho`
- `bytes`

### Validação por schema

`web_rota(..., schema, ...)` agora aceita:

- `form_obrigatorio`: campos obrigatórios de formulário;
- `arquivos_obrigatorios`: campos de arquivo obrigatórios.

Exemplo:

```trama
função upload(req)
    arq = req["arquivos"]["avatar"][0]
    retorne {"status": 200, "json": {"ok": verdadeiro, "nome": req["formulario"]["nome"], "arquivo": arq["nome_arquivo"]}}
fim

assíncrona função principal()
    app = web_criar_app()
    web_rota(app, "POST", "/upload", upload, {"form_obrigatorio": ["nome"], "arquivos_obrigatorios": ["avatar"]}, {})
    servidor = aguarde web_iniciar(app, "127.0.0.1", 8080)
    aguarde web_parar(servidor)
fim
```

## 2. Storage

### Backends

- local: `armazenamento_criar_local(base_dir)`
- S3-compatível: `armazenamento_criar_s3(bucket, endpoint_url?, access_key?, secret_key?, region?, prefixo?)`

### Operações

- `armazenamento_salvar(storage, chave, conteudo, content_type?, metadata?)`
- `armazenamento_ler(storage, chave)`
- `armazenamento_remover(storage, chave)`
- `armazenamento_listar(storage, prefixo?)`
- `armazenamento_url(storage, chave, expira_em?)`

Aliases:

- `armazenamento_local_criar`
- `armazenamento_s3_criar`

## 3. Pipeline de mídia

### API

- `midia_ler_arquivo(caminho)`
- `midia_salvar_arquivo(caminho, conteudo)`
- `midia_comprimir_gzip(conteudo, nivel?)`
- `midia_descomprimir_gzip(conteudo)`
- `midia_sha256(conteudo)`
- `midia_redimensionar_imagem(conteudo, largura, altura, manter_aspecto?, formato_saida?, qualidade?)`
- `midia_converter_imagem(conteudo, formato_saida, qualidade?)`
- `midia_pipeline(conteudo, opcoes?)`

Aliases:

- `midia_gzip_comprimir`
- `midia_gzip_descomprimir`

### Observação de dependência

As operações de imagem (`midia_redimensionar_imagem`, `midia_converter_imagem`) exigem `Pillow`.
Sem `Pillow`, a linguagem retorna erro controlado com mensagem explícita.

## 4. Exemplo rápido de storage + mídia

```trama
função principal()
    storage = armazenamento_criar_local("/tmp/trama_storage")
    dados = midia_comprimir_gzip("conteudo de exemplo", 6)
    r = armazenamento_salvar(storage, "arquivos/demo.gz", dados, "application/gzip", {"origem": "exemplo"})
    exibir(r["ok"])

    g = armazenamento_ler(storage, "arquivos/demo.gz")
    txt = midia_descomprimir_gzip(g["bytes"])
    exibir(txt)
fim
```

## 5. Testes da versão

- multipart/form-data: `tests/test_web_runtime_multipart.py`
- storage: `tests/test_storage_runtime.py`
- mídia: `tests/test_media_runtime.py`
