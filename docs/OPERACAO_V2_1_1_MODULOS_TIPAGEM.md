# Operação v2.1.1 - Módulos e Tipagem (Comando a Comando)

Guia operacional para validar recursos da v2.1.1 em ambiente local.

## 1. Verificação rápida de compilação

```bash
trama compilar-legado exemplos/v211/01_para_em_lista_soma.trm -o /tmp/v211_01.tbc
trama executar-tbc /tmp/v211_01.tbc
```

## 2. Contrato explícito de módulo

```bash
trama executar exemplos/v211/03_importe_explicito_contrato.trm
```

Esperado:

- apenas símbolos exportados são visíveis via alias importado.

## 3. Tipagem gradual fase 1

```bash
trama executar exemplos/v211/04_tipagem_fase1_basica.trm
```

## 4. Tipagem gradual fase 2

```bash
trama executar exemplos/v211/05_tipagem_fase2_compostos.trm
trama executar exemplos/v211/06_uniao_fronteira_api.trm
```

## 5. Diagnóstico negativo (estável)

```bash
trama compilar-legado exemplos/v211/07_diagnostico_retorno_invalido.trm -o /tmp/v211_negativo.tbc
```

Esperado:

- falha com `SEM0204` e contexto de linha/coluna/sugestão.

## 6. Resolução determinística multi-pacote

```bash
TRAMA_MODPATH="./exemplos/v211/pacote_b:./exemplos/v211/pacote_a" \
trama executar exemplos/v211/08_resolucao_modpath.trm
```

Troque a ordem de `TRAMA_MODPATH` para verificar precedência.

## 7. Exemplos complexos de produção

```bash
trama executar exemplos/v211/11_sistema_financeiro_completo.trm
trama executar exemplos/v211/12_sistema_atendimento_omnichannel.trm
trama executar exemplos/v211/13_orquestracao_multi_pacote.trm
trama executar exemplos/v211/14_pipeline_auditoria_tipada.trm
trama executar exemplos/v211/15_simulacao_escala_modular.trm
```

## 8. Troubleshooting rápido

- erro de import:
  - confirme caminho relativo ao arquivo de entrada;
  - valide `TRAMA_MODPATH`.
- erro semântico de tipagem:
  - procure por `SEM0203` (argumento) e `SEM0204` (retorno).
- erro de laço:
  - `SEM0306` indica iterável inválido em `para/em`.
