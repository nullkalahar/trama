# Auto-Hospedagem do Compilador (v1.0.5)

Este documento descreve o estado da meta **"Trama compilando Trama"**.

## Objetivo

- tornar o pipeline de compilação canônico em pt-BR usando código `.trm`;
- manter a implementação Python legada apenas como compatibilidade transitória;
- garantir paridade automática entre os dois caminhos.

## Componentes

- `selfhost/compilador/mod.trm`: módulo canônico de compilação em Trama;
- `selfhost/runtime/mod.trm`: base de runtime canônico em Trama;
- `scripts/build_selfhost.sh`: build oficial dos componentes self-host;
- `trama compilar`: usa pipeline self-host por padrão;
- `trama compilar-legado`: pipeline antigo em Python (compatibilidade);
- `trama semente-compilar`: compilador semente mínimo para bootstrap;
- `trama paridade-selfhost`: valida equivalência de bytecode.
- `trama executar-tbc`: executa bytecode `.tbc` sem passar por compilação.

## Novos builtins de bridge (pt-BR)

- `trama_compilar_fonte(codigo)`
- `trama_compilar_arquivo(caminho_fonte)`
- `trama_compilar_para_arquivo(caminho_fonte, caminho_saida)`

Aliases transitórios:

- `compilar_trama_fonte`
- `compilar_trama_arquivo`
- `compilar_trama_para_arquivo`

## Utilitários de coleção/estrutura

- `tamanho(valor)`
- `lista_adicionar(lista, valor)`
- `mapa_obter(mapa, chave, padrao?)`
- `mapa_definir(mapa, chave, valor)`
- `mapa_chaves(mapa)`

## Fluxo recomendado

```bash
trama compilar app.trm -o app.tbc
trama paridade-selfhost app.trm
trama executar-tbc app.tbc
```

Build de artefatos self-host:

```bash
scripts/build_selfhost.sh
```

## Estado

- pipeline self-host funcional;
- paridade automática funcional;
- implementação legada Python ainda existe para transição controlada.
