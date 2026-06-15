# Manual v2.1.32

## Leitura de upload grande

No handler HTTP:

```trama
arq = req["arquivos"]["avatar"][0]
exibir(arq["streaming"])
exibir(arq["caminho_temporario"])
exibir(arq["tamanho"])
```

Uso recomendado:
- mover o arquivo para storage formal o quanto antes
- não depender de `bytes` para arquivos grandes
