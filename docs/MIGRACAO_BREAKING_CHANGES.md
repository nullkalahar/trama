# Migracao para mudancas potencialmente quebraveis

Este guia define o protocolo oficial para evolucao com breaking changes.

## Quando considerar breaking change
- remocao ou renomeacao de API publica.
- alteracao de contrato HTTP (campos, codigos, envelopes).
- alteracao semantica incompatível com comportamento anterior.

## Protocolo obrigatorio
1. documentar mudanca em `CHANGELOG.md`.
2. criar secao de migracao nesta documentacao.
3. manter alias/compatibilidade por janela definida.
4. adicionar testes de regressao e contrato cobrindo antes/depois.
5. publicar plano de rollback.

## Modelo de secao por mudanca
- contexto
- impacto
- como migrar (passo a passo)
- exemplos antes/depois
- janela de deprecacao
- rollback

## Rollback
- reverter release para versao anterior estavel.
- restaurar comportamento legado por feature flag, quando aplicavel.
- comunicar consumidores e atualizar runbook.
