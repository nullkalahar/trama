# Manual Trama v2.1.22

## 1. Visão geral

Este manual cobre uso prático de:
- v2.1.21: base OIDC federada (discovery + validação JWT por JWKS)
- v2.1.22: autorização contextual com políticas + RBAC

## 2. Fluxo recomendado de autenticação (v2.1.21)

1. Configurar provedor OIDC:

```trm
oidc_configurar_provedor("provedor_principal", "https://id.trama.dev", "backend-trama", 2.0, 300)
```

2. Validar token recebido:

```trm
resultado = oidc_validar_token("provedor_principal", token_bearer)
```

3. Extrair identidade:

```trm
id_usuario = resultado["identidade"]["id_usuario_externo"]
```

## 3. Fluxo recomendado de autorização (v2.1.22)

1. Definir RBAC base:

```trm
modelo = rbac_criar({"admin": ["usuario:apagar"], "editor": ["doc:editar"]})
usuarios = {}
usuarios = rbac_atribuir(usuarios, "u1", "admin")
```

2. Definir políticas contextuais:

```trm
politicas = autorizacao_politicas_criar([
    {
        "id": "bloqueio_prod",
        "efeito": "negar",
        "ator": {"papeis": ["admin"]},
        "acao": "usuario:apagar",
        "contexto": {"ambiente": "producao"}
    }
], "negar")
```

3. Avaliar decisão final:

```trm
out = autorizacao_avaliar(
    modelo,
    usuarios,
    "u1",
    "usuario:apagar",
    {"tipo": "usuario", "id": "u9"},
    {"ambiente": "producao"},
    politicas
)
```

## 4. Estratégia de produção

- Manter RBAC como base estável.
- Aplicar políticas contextuais para exceções de negócio.
- Priorizar regras explícitas de negação para cenários críticos.
- Auditar `regra_id` aplicada em cada decisão sensível.

## 5. Diagnóstico rápido

- `origem_decisao = rbac`:
  - nenhuma regra contextual explícita casou.
- `origem_decisao = politica_explicita`:
  - regra contextual prevaleceu.
- `decisao_explicita = falso`:
  - efeito padrão da política foi aplicado.

## 6. Referências

- `docs/LINGUAGEM_V2_1_21.md`
- `docs/LINGUAGEM_V2_1_22.md`
- `exemplos/v221/`
- `exemplos/v222/`
