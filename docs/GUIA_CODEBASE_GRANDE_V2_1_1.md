# Guia de Codebase Grande - Trama v2.1.1

Este guia cobre práticas de arquitetura para equipes grandes usando os recursos novos da v2.1.1:

- `para/em` completo no pipeline da linguagem;
- contratos explícitos de módulo (`exporte` e `importe ... expondo ...`);
- resolução determinística de módulos multi-pacote;
- tipagem gradual em duas fases;
- diagnósticos semânticos estáveis e auditáveis.

## 1. Objetivo de arquitetura

Em bases grandes, o principal risco é acoplamento implícito. A v2.1.1 resolve isso com três mecanismos centrais:

1. fronteira explícita de módulo (`exporte`);
2. consumo explícito de símbolos (`expondo`);
3. validação estática progressiva (tipagem gradual).

## 2. Convenções oficiais recomendadas

- identificadores sempre em `snake_case` sem acento;
- um módulo exporta apenas API pública mínima;
- não exportar constantes de uso interno;
- evitar import circular entre módulos de domínio;
- usar tipos em fronteiras críticas (módulo, API, cálculo, autorização).

## 3. Organização de pastas para projeto grande

Estrutura sugerida:

```text
meu_projeto/
  app.trm
  dominio/
    usuarios.trm
    faturamento.trm
  aplicacao/
    casos_uso.trm
    validadores.trm
  infraestrutura/
    repositorios.trm
    gateways.trm
  compartilhado/
    tipos.trm
    erros.trm
```

Regra prática:

- `dominio/*` não importa `infraestrutura/*`.
- `aplicacao/*` orquestra domínio + infraestrutura.
- `app.trm` apenas composição e execução.

## 4. Contratos explícitos de módulo

### Exportação

```trm
exporte criar_usuario, buscar_usuario
```

### Importação

```trm
importe "dominio/usuarios.trm" como usuarios expondo criar_usuario, buscar_usuario
```

Benefícios:

- reduz colisão de símbolos;
- evita dependência acidental de função interna;
- facilita refatoração com menor risco.

## 5. Tipagem gradual na prática

## Fase 1

- começar por assinatura de função e variáveis críticas;
- manter legado não anotado funcionando.

```trm
função calcular_total(itens: lista[inteiro]): inteiro
    total: inteiro = 0
    para i em itens
        total = total + i
    fim
    retorne total
fim
```

## Fase 2

- usar tipos compostos e união na fronteira entre módulos.

```trm
função normalizar_id(valor: uniao[inteiro|texto]): texto
    retorne json_stringify({"id": valor})
fim
```

## 6. Resolução de módulos (determinística)

Ordem de busca oficial do runtime Python:

1. diretório do arquivo atual;
2. entradas de `TRAMA_MODPATH` (na ordem declarada);
3. diretório de execução atual (`cwd`).

Para referência `importe "pacote" ...`, são testados:

- `pacote.trm`
- `pacote/mod.trm`
- `pacote/__init__.trm`

## 7. Diagnóstico semântico estável

Erros semânticos têm contrato previsível com:

- código (`SEMxxxx`)
- mensagem estável
- `linha` e `coluna`
- sugestão de correção

Exemplo:

- `SEM0203`: argumento incompatível em chamada tipada.
- `SEM0204`: retorno incompatível com assinatura.
- `SEM0306`: iterável inválido em `para/em`.

## 8. Playbook de refatoração segura

1. adicione `exporte` nos módulos de domínio antes da mudança;
2. converta imports para `expondo` explicitamente;
3. anote tipos em assinaturas públicas;
4. rode suíte de regressão;
5. só depois refatore implementação interna.

## 9. Checklist para PR em base grande

- módulo novo tem `exporte` explícito;
- import novo usa `expondo`;
- fronteira pública tipada;
- testes de cenário positivo/negativo;
- erro esperado possui código semântico estável;
- documentação de módulo atualizada.

## 10. Troubleshooting

- `Módulo não encontrado`:
  - valide `source_path` e `TRAMA_MODPATH`.
- `SEM0404` (exporte nome não declarado):
  - garanta que símbolo exportado exista no módulo.
- `SEM0203/SEM0204` após migração:
  - alinhe assinatura tipada com valores reais de entrada/retorno.

## 11. Referências

- `docs/LINGUAGEM_V2_1_1.md`
- `docs/MANUAL_TRAMA_COMPLETO_V2_1_1.md`
- `exemplos/v211/`
