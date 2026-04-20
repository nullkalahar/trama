# Trama v2.0.1 - ORM e migracoes nivel producao

## 1. Escopo da versao

A `v2.0.1` consolida a camada de dados da Trama para operacao de backend em producao, com foco em:
- ORM com relacoes completas;
- migracoes versionadas com trilha e rollback;
- seeds deterministicas por ambiente;
- diff de schema com preview antes de aplicar;
- superficie oficial canonicamente pt-BR.

## 2. Superficie canonica pt-BR

Forma oficial em pt-BR (snake_case, sem acento em identificadores):
- relacoes ORM: `orm_relacao_um_para_um`, `orm_relacao_um_para_muitos`, `orm_relacao_muitos_para_muitos`;
- operacoes ORM: `orm_modelo`, `orm_inserir`, `orm_atualizar`, `orm_buscar_por_id`, `orm_listar`;
- schema/constraints: `schema_constraint_unica`, `schema_constraint_fk`, `schema_constraint_check`, `schema_definir`, `schema_inspecionar`, `schema_diff`, `schema_preview_plano`, `schema_aplicar_diff`;
- migracao/seed: `migracao_aplicar_versionada_v2`, `migracao_trilha_listar`, `migracao_reverter_ultima`, `seed_aplicar_ambiente`.

Aliases em ingles existem apenas para compatibilidade retroativa.

## 3. Capacidades principais

### 3.1 Relacoes e consultas ORM

- relacoes 1:1, 1:N e N:N;
- preload/eager/lazy em listagem;
- paginacao por `pagina/limite` e por `cursor`;
- ordenacao deterministica.

### 3.2 Schema e constraints

- definicao declarativa de schema com constraints:
  - unica simples e composta;
  - chave estrangeira;
  - check de consistencia;
- inspecao de schema atual;
- geracao de diff e preview de plano;
- aplicacao controlada de diff.

### 3.3 Migracoes e seeds

- migracao versionada idempotente;
- trilha de execucao consultavel;
- rollback seguro da ultima migracao;
- seed por ambiente (`dev`, `teste`, `prod`) com rastreabilidade.

## 4. Exemplo rapido (.trm)

```trm
assíncrona função principal()
    conn = aguarde banco_conectar("sqlite:////tmp/trama_v201_demo.db")

    aguarde migracao_aplicar_versionada_v2(
        conn,
        "201.001",
        "criar_tabela_usuarios",
        "CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL);",
        "DROP TABLE IF EXISTS usuarios;",
        "dev"
    )

    aguarde seed_aplicar_ambiente(
        conn,
        "dev",
        "seed_usuarios_iniciais",
        "INSERT INTO usuarios (nome, email) VALUES ('Admin', 'admin@local');"
    )

    linhas = aguarde banco_consultar(conn, "SELECT id, nome, email FROM usuarios ORDER BY id")
    exibir(linhas)

    trilha = aguarde migracao_trilha_listar(conn, 10)
    exibir(trilha)

    aguarde banco_fechar(conn)
fim
```

## 5. DoD v2.0.1 (atendido)

- pipeline de migracao idempotente;
- rollback validado em cenarios reais;
- documentacao operacional de banco atualizada;
- testes unitarios e integracao cobrindo banco vazio e legado.

## 6. Evidencias no repositorio

Codigo:
- `src/trama/db_runtime.py`
- `src/trama/builtins.py`
- `src/trama/semantic.py`

Testes:
- `tests/test_db_runtime.py`
- `tests/test_vm.py` (cenarios de DB e integracao VM)
- `.local/tests/v2_0_1_db_orm/run_local_v201.sh`

Exemplos:
- `exemplos/v201/README_V201_EXEMPLOS.md`
- `exemplos/v201/201_relacoes_orm.trm` ate `exemplos/v201/215_migracao_compatibilidade_assinatura.trm`

## 7. Operacao recomendada

1. aplicar migracoes versionadas;
2. aplicar seed por ambiente;
3. validar trilha de migracoes;
4. executar testes de regressao de contrato/dados antes de release.

Comando util de validacao local:

```bash
.venv/bin/python -m pytest -q tests/test_db_runtime.py
```
