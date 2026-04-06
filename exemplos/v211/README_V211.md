# Exemplos v2.1.1

Arquivos desta pasta cobrem os recursos da versão v2.1.1:

1. `01_para_em_lista_soma.trm`: laço `para/em` básico.
2. `02_para_em_com_pare_continue.trm`: controle de fluxo com `pare`/`continue`.
3. `03_importe_explicito_contrato.trm`: `importe ... expondo ...` + `exporte`.
4. `04_tipagem_fase1_basica.trm`: anotações de parâmetro/retorno/variável.
5. `05_tipagem_fase2_compostos.trm`: tipo composto `lista[inteiro]`.
6. `06_uniao_fronteira_api.trm`: tipo `uniao[...]` em fronteira de função.
7. `07_diagnostico_retorno_invalido.trm`: cenário negativo com diagnóstico semântico.
8. `08_resolucao_modpath.trm`: resolução determinística com `TRAMA_MODPATH`.
9. `09_contrato_modulo_exportes_multiplos.trm`: contrato de módulo com múltiplos exports.
10. `10_migracao_legado_para_tipado.trm`: adoção progressiva em código legado.
11. `11_sistema_financeiro_completo.trm`: exemplo grande multi-módulo com normalização, risco e relatório.
12. `12_sistema_atendimento_omnichannel.trm`: exemplo grande de priorização/SLA/indicadores.
13. `13_orquestracao_multi_pacote.trm`: composição entre pacotes com import determinístico.
14. `14_pipeline_auditoria_tipada.trm`: pipeline tipado de eventos administrativos.
15. `15_simulacao_escala_modular.trm`: processamento de lotes em escala com laços aninhados.

## Execução

```bash
trama executar exemplos/v211/01_para_em_lista_soma.trm
trama executar exemplos/v211/03_importe_explicito_contrato.trm
trama executar exemplos/v211/04_tipagem_fase1_basica.trm
trama executar exemplos/v211/11_sistema_financeiro_completo.trm
trama executar exemplos/v211/12_sistema_atendimento_omnichannel.trm
```

Para validar um exemplo negativo:

```bash
trama compilar-legado exemplos/v211/07_diagnostico_retorno_invalido.trm -o /tmp/ignorar.tbc
```

Esperado: erro semântico `SEM0204` com linha/coluna/sugestão.
