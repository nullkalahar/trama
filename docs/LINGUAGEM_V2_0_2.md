# Linguagem Trama v2.0.2 (DTO, validação e contrato HTTP)

Esta versão introduz camada declarativa de DTO para requisições HTTP, validação profunda com erros por campo e contrato de resposta versionado com retrocompatibilidade.

## Objetivo

- validação uniforme de entrada em rotas HTTP;
- erros previsíveis e estáveis para domínio/validação;
- contrato HTTP versionado e documentado.

## API canônica pt-BR

- `web_rota_dto(app, metodo, caminho, handler, dto_requisicao, contrato_resposta?, schema?, opcoes?)`
- `dto_validar(dto_requisicao, payload, contexto?)`
- `dto_gerar_exemplos(dto_requisicao, contexto?)`

Alias de compatibilidade:

- `web_rota_com_dto` (alias de `web_rota_dto`)

## DTO declarativo

O DTO pode ser definido por contexto (`corpo`, `consulta`, `parametros`, `formulario`) e suporta validação profunda.

Exemplo:

```trama
dto = {
    "corpo": {
        "tipo": "objeto",
        "permitir_campos_extras": falso,
        "campos": {
            "nome": {"tipo": "texto", "obrigatorio": verdadeiro, "sanitizar": {"trim": verdadeiro}},
            "idade": {"tipo": "inteiro", "coagir": verdadeiro, "minimo": 0},
            "ativo": {"tipo": "logico", "coagir": verdadeiro, "padrao": verdadeiro},
            "tags": {"tipo": "lista", "itens": {"tipo": "texto", "sanitizar": {"trim": verdadeiro}}}
        }
    }
}
```

Campos suportados no spec:

- `tipo`: `texto`, `inteiro`, `numero`, `logico`, `lista`, `objeto` (`mapa`/`dict` também aceitos).
- `obrigatorio`: exige presença do campo.
- `padrao`: valor default quando ausente.
- `permitir_nulo`: aceita `nulo`.
- `coagir`: tenta converter tipo de entrada (ex.: `"33"` -> inteiro).
- `sanitizar`: regras de texto (`trim`, `colapsar_espacos`, `minusculo`, `maiusculo`, `remover_acentos`, `remover_html`).
- limites: `minimo`, `maximo`, `tamanho_min`, `tamanho_max`.
- coleções: `itens` (spec do item).
- objetos: `campos`/`propriedades`, `permitir_campos_extras`.
- `enum`: conjunto de valores permitidos.

## Erro padronizado por campo

Quando a validação falha, a resposta retorna:

```json
{
  "ok": false,
  "erro": {
    "codigo": "VALIDACAO_FALHOU",
    "mensagem": "Falha de validação da requisição.",
    "detalhes": {
      "campos": [
        {
          "codigo": "TIPO_INVALIDO",
          "campo": "corpo.idade",
          "mensagem": "Tipo inválido.",
          "detalhes": {"tipo_esperado": "inteiro"}
        }
      ]
    }
  }
}
```

## Sanitização e remoção de campos proibidos

Use `contrato_entrada.campos_permitidos` em `opcoes` da rota para sanitização estrutural:

```trama
opcoes = {
    "contrato_entrada": {
        "campos_permitidos": {
            "corpo": ["nome", "idade", "ativo"]
        }
    }
}
```

Campos fora da lista permitida são removidos automaticamente antes do handler.

## Contrato de resposta versionado e retrocompatível

`contrato_resposta` agora suporta múltiplas versões:

```trama
contrato = {
    "versao_padrao": "v2",
    "versoes": {
        "v1": {"envelope": verdadeiro, "campos_obrigatorios": ["ok", "dados", "erro", "meta"]},
        "v2": {"envelope": verdadeiro, "campos_obrigatorios": ["ok", "dados", "erro", "meta", "links"]}
    },
    "retrocompativel": {"legacy": "v1"}
}
```

Resolução de versão:

- header: `X-Contrato-Versao` (ou `X-Api-Contract-Version`);
- query: `versao_contrato` (ou `contract_version`);
- fallback: `versao_padrao`;
- retrocompatibilidade explícita via `retrocompativel`.

Headers de saída:

- `X-Contrato-Versao-Solicitada`
- `X-Contrato-Versao-Aplicada`

Em versão inválida:

- status `400`
- código `CONTRATO_VERSAO_INVALIDA`

## Geração de exemplos para testes

`dto_gerar_exemplos(dto, "corpo")` retorna payloads base válidos e inválidos esperados para acelerar criação de testes de contrato/validação.

## Cobertura de testes

- `tests/test_web_runtime_v202.py`
- `tests/test_vm.py::test_v202_dto_contrato_versionado_em_vm`
