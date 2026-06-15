# Manual v2.1.33

## Geração de variantes

```trama
resultado = midia_pipeline_storage(storage, "origens/a.bin", "midia/a", {
    "variantes": [
        {"nome": "gzip", "opcoes": {"comprimir_gzip": verdadeiro, "nivel_gzip": 6}, "chave": "midia/a/a.bin.gz"},
        {"nome": "copia", "acao": "copiar", "chave": "midia/a/a.bin"}
    ]
})
```

Saídas:
- variantes persistidas no storage
- `manifesto.json`
- metadados de origem e de cada variante
