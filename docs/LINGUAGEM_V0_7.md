# Linguagem trama v0.7

A `v0.7` adiciona segurança de aplicação backend: autenticação, hash de senha e autorização por papéis.

## JWT

- `jwt_criar(payload, segredo, exp_segundos?, algoritmo?)`
- `jwt_verificar(token, segredo, leeway_segundos?)`

Aliases em pt-BR:

- `token_criar`
- `token_verificar`

## Senhas

- `senha_hash(senha, algoritmo?)`
- `senha_verificar(senha, hash_armazenado)`

Algoritmos:

- `pbkdf2` (disponível nativamente)
- `bcrypt` (quando dependência estiver instalada)
- `argon2`/`argon2id` (quando dependência estiver instalada)

Aliases em pt-BR:

- `senha_gerar_hash`
- `senha_validar`

## RBAC

- `rbac_criar(papeis_permissoes, heranca_papeis?)`
- `rbac_atribuir(usuarios_papeis, usuario, papel)`
- `rbac_papeis_usuario(usuarios_papeis, usuario)`
- `rbac_tem_papel(usuarios_papeis, usuario, papel)`
- `rbac_tem_permissao(modelo, usuarios_papeis, usuario, permissao)`

Aliases em pt-BR:

- `papel_criar_modelo`
- `papel_atribuir`
- `papel_listar_usuario`
- `papel_tem`
- `permissao_tem`

## Exemplo

```trm
função principal()
    h = senha_hash("abc123", "pbkdf2")
    exibir(senha_verificar("abc123", h))

    token = token_criar({"sub": "u1", "papel": "admin"}, "segredo", 3600)
    claims = token_verificar(token, "segredo")
    exibir(claims["sub"])

    modelo = papel_criar_modelo({"admin": ["users:write"], "viewer": ["users:read"]}, {"admin": ["viewer"]})
    usuarios = {}
    usuarios = papel_atribuir(usuarios, "u1", "admin")
    exibir(permissao_tem(modelo, usuarios, "u1", "users:read"))
fim
```
