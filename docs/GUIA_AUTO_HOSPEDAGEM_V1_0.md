# Guia de Auto-hospedagem e Operação (v1.0)

Este guia define o padrão mínimo de operação para backend Trama em produção.

## 1. Pré-requisitos

- Linux x86_64
- acesso a banco (SQLite/PostgreSQL)
- observabilidade habilitada (`log_estruturado`, métricas e tracing)
- backup automatizado de banco e arquivos

## 2. Build e distribuição

```bash
scripts/build_standalone.sh
scripts/package_deb.sh 0.9.0 amd64
sudo apt install ./build/trama_0.9.0_amd64.deb
```

## 3. Modelo de execução

- 1 processo por serviço
- health endpoints canônicos:
  - `/saude`
  - `/pronto`
  - `/vivo`
- timeout de requests e limites de payload ativos

## 4. SLO/SLI mínimos

- disponibilidade mensal: 99.5%
- latência p95 em rotas críticas: <= 250ms (baseline inicial)
- taxa de erro 5xx: < 1%

## 5. Checklist de release

- testes unitários: ok
- testes de integração HTTP/DB: ok
- carga básica (baseline): ok
- migrações versionadas aplicadas em staging: ok
- rollback validado: ok
- documentação atualizada: ok

## 6. Backup e restore

- backup diário do banco
- retenção mínima de 7 dias
- teste de restauração semanal em staging

## 7. Runbooks essenciais

- banco indisponível: reduzir tráfego, validar conexão, aplicar fallback e rollback se necessário
- aumento de latência: analisar métricas p95/p99, queries lentas e rate-limit
- erro em webhook/job: revisar DLQ, reprocessar jobs com idempotência

## 8. Segurança operacional

- segredos fora do código-fonte
- rotação periódica de chaves JWT
- rate-limit em rotas sensíveis
- revisão de permissões RBAC por rota
