# Manual v2.1.34

## Políticas e URL assinada

```trama
armazenamento_definir_politicas(storage, {
    "visibilidade": "publico",
    "lifecycle_dias": 7
})
armazenamento_salvar(storage, "docs/a.txt", "oi", "text/plain")
meta = armazenamento_metadados(storage, "docs/a.txt")
url = armazenamento_url_assinada(storage, "docs/a.txt", 120, "baixar")
```

Resultados:
- políticas refletidas em metadados
- URL temporária para consumo controlado
