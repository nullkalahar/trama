# Roadmap de Implementações Futuras (v2.1.x)

Este documento detalha o plano de evolução da Trama para uso real em retaguarda de aplicações SaaS de grande porte.

Objetivo: transformar os 7 eixos críticos em entregas versionadas, com escopo claro e critério de pronto.

## Princípios de versionamento

- cada versão `v2.1.x` fecha um eixo crítico completo;
- nenhuma versão é considerada concluída sem testes automatizados e documentação;
- mudanças de linguagem devem priorizar compatibilidade retroativa;
- quebra de compatibilidade só entra com plano explícito de migração;
- toda funcionalidade nova deve ter medição operacional (telemetria e diagnóstico).

## Visão geral das versões

| Versão | Eixo crítico | Resultado esperado |
|---|---|---|
| `v2.1.1` | Runtime 100% nativo | `executar`/`compilar` nativos sem ponte Python |
| `v2.1.2` | Concorrência e desempenho de servidor | servidor com modelo concorrente robusto e medição reproduzível |
| `v2.1.3` | Camada de dados enterprise | banco/migração/ORM prontos para produção multi-serviço |
| `v2.1.4` | Componentes distribuídos | cache, fila e observabilidade desacoplados do processo local |
| `v2.1.5` | Segurança de produção | autenticação/autorização e hardening com nível de produção |
| `v2.1.6` | Ferramentas de engenharia | integração contínua/entrega contínua, qualidade e experiência de desenvolvimento para equipes grandes |
| `v2.1.7` | Linguagem para código grande | `para/em` completo, módulos sólidos, tipagem gradual e governança de código |

---

## v2.1.1 - Runtime 100% nativo (sem ponte)

### Escopo

- retaguarda nativa para `trama executar arquivo.trm`;
- retaguarda nativa para `trama compilar arquivo.trm -o arquivo.tbc`;
- import nativo direto de `.trm` com resolução de módulos consistente;
- remoção da dependência de ponte Python no caminho crítico de execução/compilação.

### Entregas obrigatórias

- CLI nativa com diagnóstico real (`--diagnostico-runtime`) indicando retaguarda 100% nativa;
- suíte de paridade funcional entre ambiente de execução Python e ambiente de execução nativo para cenários equivalentes;
- documentação de diferenças conhecidas (se houver) e plano de convergência.

### Critério de pronto v2.1.1

- `executar`, `compilar` e `executar-tbc` operam sem Python no host;
- testes de regressão da linguagem aprovados no ambiente nativo;
- versão autônoma (`standalone`) e `.deb` publicados com retaguarda nativa validada.

---

## v2.1.2 - Concorrência e desempenho de servidor

### Escopo

- modelo concorrente de ambiente de execução HTTP com estratégia clara de escalabilidade;
- agendador assíncrono completo (não apenas `aguarde` sequencial);
- controle de tempo limite/cancelamento/retenção de carga em E/S e tratadores;
- suporte a encerramento gracioso e drenagem de conexões.

### Entregas obrigatórias

- metas oficiais de medição (requisições por segundo, p95/p99, memória) por perfil de carga;
- testes de carga e resistência prolongada com cenários de concorrência alta;
- configuração de limites operacionais por ambiente (desenvolvimento/homologação/produção).

### Critério de pronto v2.1.2

- linha de base de desempenho reproduzível e versionada;
- ausência de vazamentos críticos em teste prolongado;
- observabilidade cobrindo saturação, fila interna e latência.

---

## v2.1.3 - Camada de dados enterprise

### Escopo

- pool de conexões configurável por ambiente;
- políticas de retry/backoff por classe de erro;
- migrações versionadas com bloqueio confiável e reversão segura;
- evolução de ORM/construtor de consulta para relações e paginação robustas.

### Entregas obrigatórias

- testes de migração em banco vazio, banco com dados e banco legado;
- testes de concorrência em transações e locks;
- documentação de estratégia de mudanças de schema sem downtime.

### Critério de pronto v2.1.3

- migrações e reversão validadas em esteira automatizada;
- operações críticas com comportamento consistente sob falha;
- guias operacionais de banco publicados.

---

## v2.1.4 - Componentes distribuídos (cache, filas e telemetria)

### Escopo

- cache distribuído com TTL/invalidação multi-instância;
- filas com retaguarda persistente e fila de descarte real;
- transporte de eventos em tempo real para múltiplas instâncias (plano de distribuição);
- exportação de telemetria para sistema externo (não só memória local).

### Entregas obrigatórias

- modo de compatibilidade local para desenvolvimento;
- testes de falha parcial (nó indisponível, rede intermitente, reconexão);
- métricas de consistência (hit ratio, atraso de fila, perda/reentrega).

### Critério de pronto v2.1.4

- execução horizontal sem inconsistência crítica entre nós;
- recuperação automática em cenários de falha previstos;
- documentação de topologia de produção e limites conhecidos.

---

## v2.1.5 - Segurança de produção

### Escopo

- evolução de autenticação: rotação/revogação de tokens, sessões e dispositivos;
- reforço de borda HTTP (cabeçalhos, CORS estrito, limites de carga útil, proteção contra abuso);
- trilha de auditoria para ações sensíveis;
- gestão de segredos para produção (integração com gerenciador externo).

### Entregas obrigatórias

- suíte de testes de segurança (autenticação/autorização, contorno indevido, abuso de limite de taxa);
- políticas mínimas de criptografia, senha e retenção de logs;
- lista de verificação de segurança pré-lançamento.

### Critério de pronto v2.1.5

- controles de autenticação/autorização validados ponta a ponta;
- trilha de auditoria consultável para eventos administrativos;
- linha de base de segurança documentada e repetível.

---

## v2.1.6 - Ferramentas de engenharia para equipes grandes

### Escopo

- integração contínua/entrega contínua oficial versionada (compilação, teste, lint, pacote, lançamento);
- qualidade de linguagem: lint/formatação/cobertura mais completos;
- testes de integração/ponta a ponta/carga na esteira;
- modelos de projeto para retaguarda real com convenções de equipe.

### Entregas obrigatórias

- esteira de qualidade obrigatória para mesclagem;
- versionamento semântico e changelog por versão;
- guias de contribuição, manutenção e resposta a incidentes.

### Critério de pronto v2.1.6

- fluxo de desenvolvimento padronizado para múltiplos times;
- etapa de qualidade impedindo regressão crítica;
- integração técnica inicial reproduzível com documentação oficial.

---

## v2.1.7 - Linguagem para código grande (ponto crítico)

Este é o eixo de maior impacto para manter sistemas SaaS de grande porte ao longo dos anos.

### Problema atual (estado real)

- `para`/`em` aparecem no lexer como keywords, mas sem implementação completa no parser/AST/compilador/VM;
- análise semântica ainda centrada no núcleo dinâmico;
- ausência de tipagem gradual e de contratos de módulo reduz previsibilidade em bases de código grandes.

### Meta de produto da linguagem

Permitir manutenção sustentável de projetos grandes, com:

- legibilidade em fluxos complexos;
- segurança de refatoração;
- contratos explícitos entre módulos;
- redução de erro em tempo de execução.

### Subfases obrigatórias de v2.1.7

#### v2.1.7-a - Fechamento sintático/semântico de `para/em`

- gramática oficial para `para identificador em expressão`;
- AST dedicada para laço de iteração;
- compilação para bytecode com semântica de `pare/continue` consistente;
- execução na VM (Python e nativa) com paridade;
- mensagens de erro claras para uso inválido.

Critério de pronto `v2.1.7-a`:

- paridade total `lexer -> parser -> AST -> semantic -> compiler -> VM` para `para/em`;
- testes unitários e de integração cobrindo listas, mapas e iteráveis futuros;
- documentação da sintaxe e comportamento publicada.

#### v2.1.7-b - Módulos e arquitetura para base de código grande

- contrato de módulo explícito (exportações e importações previsíveis);
- namespaces para evitar colisão de símbolos;
- resolução de módulos determinística (incluindo diretórios e pacotes);
- regras de organização de projeto em larga escala.

Critério de pronto `v2.1.7-b`:

- comportamento de import/export estável e testado;
- suporte a projeto multi-módulo sem ambiguidade de resolução;
- guia oficial de arquitetura de pastas e módulos.

#### v2.1.7-c - Tipagem gradual (fase 1)

- anotações de tipo opcionais em variáveis, parâmetros e retorno;
- modo misto: código sem anotação continua válido;
- checagens estáticas de inconsistências óbvias antes de executar;
- erros semânticos mais precisos (arquivo/linha/trecho/contexto).

Critério de pronto `v2.1.7-c`:

- verificador de tipos incremental com configuração por projeto;
- sem quebra de compatibilidade para código legado sem tipos;
- documentação de adoção progressiva publicada.

#### v2.1.7-d - Tipagem gradual (fase 2, robustez)

- tipos compostos essenciais (lista/mapa/função) com inferência básica;
- contratos/interfaces de dados para fronteira de API;
- validação de compatibilidade entre módulos em compilação;
- linha de base de desempenho da análise estática em projetos grandes.

Critério de pronto `v2.1.7-d`:

- checagem de tipos suficiente para reduzir erros comuns de produção;
- tempo de análise aceitável em base de código grande;
- relatório de diagnóstico com severidade por categoria.

### Regras de compatibilidade em v2.1.7

- código legado dinâmico permanece executável por padrão;
- recursos novos entram atrás de sinalizadores de linguagem quando necessário;
- deprecações têm janela mínima de duas versões menores;
- toda quebra potencial exige guia de migração automatizável.

### Métricas de sucesso de v2.1.7

- redução de erro de ambiente de execução em fluxos cobertos por tipagem;
- redução de regressão em refatorações de módulos;
- aumento de cobertura de contratos estáticos no código de referência;
- tempo de integração inicial menor em projeto grande.

---

## Critério final de prontidão para SaaS (após v2.1.7)

A Trama será considerada apta para retaguarda SaaS de grande porte quando:

- ambiente de execução nativo estiver consolidado e auditado;
- componentes distribuídos estiverem estáveis em produção;
- segurança, observabilidade e operação tiverem linha de base madura;
- linguagem oferecer recursos concretos para manutenção de base de código grande;
- esteira de engenharia impedir regressão estrutural.
