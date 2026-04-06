# Exemplos v2.0.9 - Runtime 100% nativo

Colecao de exemplos oficiais da v2.0.9 para compilacao/execucao nativa, import de modulo `.trm` e async concorrente.

## Como rodar

```bash
bash scripts/build_native_stub.sh
./dist/native/trama-native executar exemplos/v209/209_01_compilacao_nativa_basica.trm
```

## Indice

- `209_01_compilacao_nativa_basica.trm`: fluxo minimo de compilacao/execucao nativa.
- `209_02_compilar_e_executar_tbc.trm`: foco em `.trm -> .tbc -> executar-tbc`.
- `209_03_importe_nativo_modulo.trm`: import de modulo `.trm` com autocompilacao nativa.
- `209_modulo_matematica.trm`: modulo de suporte para import nativo.
- `209_04_async_tarefas_timeout_cancelar.trm`: tarefa concorrente + timeout + cancelamento.
- `209_05_async_aliases_compatibilidade.trm`: aliases em ingles de compatibilidade.
- `209_06_diagnostico_runtime_nativo.md`: leitura guiada do diagnostico oficial.
- `209_07_importe_multimodulo_relativo.trm`: import relativo em cadeia.
- `209_modulo_auxiliar_relativo.trm`: modulo auxiliar para cadeia de import.
- `209_08_erros_deterministicos_importe.trm`: exemplo de erro deterministico de import.
