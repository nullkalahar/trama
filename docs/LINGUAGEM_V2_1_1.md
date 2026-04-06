# Trama v2.1.1 - Linguagem para codebase grande

Este manual descreve a entrega integral da v2.1.1 da Trama, com foco em manutenção de bases grandes: `para/em`, contratos de módulo explícitos, resolução determinística de módulos, tipagem gradual (fases 1 e 2) e diagnósticos semânticos estáveis.

## Escopo entregue

- `para/em` implementado em parser, AST, compilador e VM Python.
- execução de bytecode com `para/em` validada também na VM nativa.
- contratos de módulo explícitos:
  - `exporte nome1, nome2`
  - `importe "caminho/mod.trm" como alias expondo nome1, nome2`
- resolução determinística de módulo no runtime Python:
  - ordem fixa de busca: diretório base do arquivo atual -> `TRAMA_MODPATH` -> `cwd`.
  - candidatos por referência: `.trm`, `mod.trm`, `__init__.trm`.
- tipagem gradual fase 1:
  - anotações opcionais em variável, parâmetro e retorno.
  - validação estática básica quando há anotação.
- tipagem gradual fase 2:
  - tipos compostos: `lista[t]`, `mapa[k,v]`, `uniao[a|b]`.
  - validação de chamada entre fronteiras de função/módulo.
- diagnósticos semânticos padronizados com:
  - `codigo`, `mensagem`, `linha`, `coluna`, `sugestao`.

## Sintaxe canônica nova

### `para/em`

```trm
para item em lista_itens
    exibir(item)
fim
```

Observação: na v2.1.1, a semântica de iteração é garantida para listas (e compatível para valores dinâmicos não anotados).

### Contrato de exportação

```trm
exporte soma, media

função soma(a: inteiro, b: inteiro): inteiro
    retorne a + b
fim
```

### Import com contrato explícito

```trm
importe "mods/matematica.trm" como mat expondo soma

função principal()
    exibir(mat["soma"](2, 3))
fim
```

## Tipagem gradual

### Fase 1 - anotações opcionais

```trm
função dobro(x: inteiro): inteiro
    retorne x * 2
fim

contador: inteiro = 10
```

### Fase 2 - tipos compostos e união

```trm
função reduzir(nums: lista[inteiro]): inteiro
    total: inteiro = 0
    para n em nums
        total = total + n
    fim
    retorne total
fim

valor: uniao[inteiro|texto] = 10
valor = "ok"
```

## Diagnósticos semânticos

Formato estável de erro semântico:

- `SEMxxxx: mensagem | linha=N | coluna=M | sugestao=...`

Exemplo real de diagnóstico:

- retorno incompatível:
  - código: `SEM0204`
  - mensagem: retorno incompatível com anotação da função
  - contexto: linha/coluna da instrução `retorne`

## Resolução de módulos (determinística)

Para `importe "pacote" como p`, o runtime tenta, em ordem:

1. `<base>/pacote.trm`
2. `<base>/pacote/mod.trm`
3. `<base>/pacote/__init__.trm`
4. repete em cada diretório de `TRAMA_MODPATH`
5. repete em `cwd`

Essa ordem é estável e reproduzível.

## Compatibilidade retroativa

- código legado sem anotação continua válido.
- aliases de compatibilidade seguem aceitos; a forma oficial continua canônica pt-BR.
- diagnósticos adicionados sem quebrar contratos anteriores da CLI/VM.

## Testes da versão

Cobertura adicionada/atualizada:

- `tests/test_linguagem_v211.py`
  - parser/AST para `para/em`, `exporte`, `importe ... expondo ...` e tipos.
  - tipagem gradual positiva/negativa.
  - diagnósticos semânticos estáveis.
  - integração VM Python com contratos e resolução determinística.
- `tests/test_native_runtime_v211.py`
  - paridade VM nativa para bytecode com `para/em`.
  - import explícito em bytecode com execução nativa.

## Troubleshooting

- erro `SEM0306` em `para/em`:
  - causa: iterável incompatível com o laço.
  - ação: use `lista[...]` (ou valor dinâmico que seja lista em runtime).
- erro de import de símbolo explícito:
  - causa: símbolo não exposto no módulo importado.
  - ação: ajuste `exporte` no módulo de origem ou `expondo` no import.
- módulo não encontrado:
  - valide `source_path` da execução e `TRAMA_MODPATH`.

## Exemplos práticos

Veja `exemplos/v211/` para cenários completos de uso em projeto grande.

Exemplos grandes recomendados:

- `exemplos/v211/11_sistema_financeiro_completo.trm`
- `exemplos/v211/12_sistema_atendimento_omnichannel.trm`
- `exemplos/v211/13_orquestracao_multi_pacote.trm`
- `exemplos/v211/14_pipeline_auditoria_tipada.trm`
- `exemplos/v211/15_simulacao_escala_modular.trm`

Leituras complementares:

- `docs/GUIA_CODEBASE_GRANDE_V2_1_1.md`
- `docs/OPERACAO_V2_1_1_MODULOS_TIPAGEM.md`
