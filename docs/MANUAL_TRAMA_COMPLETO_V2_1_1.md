# Manual Completo Trama até v2.1.1

Este documento consolida o estado funcional da Trama até a v2.1.1.

## Referência consolidada por versão

- Base histórica e evolução até v2.1.0:
  - `docs/MANUAL_TRAMA_COMPLETO_V2_1_0.md`
- Incremento desta versão:
  - `docs/LINGUAGEM_V2_1_1.md`

## Novidades consolidadas da v2.1.1

- fechamento da sintaxe e execução de `para/em` no pipeline da linguagem;
- contratos explícitos de módulo com `exporte` e `importe ... expondo ...`;
- resolução determinística de módulos com suporte a múltiplas raízes (`TRAMA_MODPATH`);
- tipagem gradual em duas fases com validação estática sem quebrar legado dinâmico;
- diagnósticos semânticos com código estável + contexto (`linha`, `coluna`, `sugestao`);
- paridade de execução validada em VM Python e VM nativa para os recursos novos.

## Superfície canônica pt-BR (v2.1.1)

- `para`, `em`, `exporte`, `expondo`, `importe`, `como`
- tipagem opcional canônica:
  - `nome: tipo = valor`
  - `função f(a: tipo): retorno`

## Qualidade e regressão

Suítes relevantes executadas para esta consolidação:

- `tests/test_lexer.py`
- `tests/test_parser.py`
- `tests/test_semantic.py`
- `tests/test_vm.py`
- `tests/test_native_runtime_v209.py`
- `tests/test_linguagem_v211.py`
- `tests/test_native_runtime_v211.py`

Resultado: aprovado.

## Exemplos oficiais

- `exemplos/v211/` (casos reais da versão v2.1.1)

## Observação operacional

Para detalhes de sintaxe, troubleshooting e contratos da versão, consulte diretamente:

- `docs/LINGUAGEM_V2_1_1.md`
