# Exemplos v2.1.3

Colecao extensa de exemplos da v2.1.3 para backend/frontend/pwa/operacao.

## Cobertura

- linguagem base e padroes de modulo;
- contratos HTTP e envelope de erro estavel;
- fluxos de backend (auth, obreiros, reunioes, visitantes, dashboard);
- dados nativos (migracao/seed/diagnostico);
- testes avancados v2.1.3 e operacao/release.

## Quantidade

Esta pasta contem 88 exemplos `.trm` (`213_01` ate `213_88`), um conjunto de arquitetura grande em `sistema_grande_v213/` e um backend funcional ARLS em `.trm` (`arls_amm_trm/`).

Exemplos grandes adicionados no fechamento:
- `213_86_backend_arls_api_http_completa.trm`;
- `213_87_reunioes_chanceler_fluxo.trm`;
- `213_88_dados_nativos_migracao_seed_diag.trm`.

## Sugestao de estudo

1. Comece por `213_01` a `213_12` (linguagem base).
2. Siga para `213_13` a `213_36` (backend/contrato).
3. Depois `213_37` a `213_52` (dados nativos).
4. Depois `213_53` a `213_68` (frontend/pwa em alto nivel).
5. Feche com `213_69` a `213_88` (operacao, teste, release, API ARLS e cadeia de dados nativa).
6. Estude `sistema_grande_v213/` para organizacao multi-modulo.
7. Estude `arls_amm_trm/` para backend de dominio com auth/obreiros/visitantes/reunioes/dashboard.
