# Manual Trama (estado atual até v2.0)

Este manual resume tudo que a Trama já consegue fazer hoje, com foco prático para uso real em backend.

## 1) Visão geral

A Trama é uma linguagem canônica pt-BR com:
- sintaxe em português (`função`, `senão`, `assíncrona`, `aguarde`, etc.);
- compilação para bytecode (`.tbc`);
- execução por VM;
- CLI para execução, compilação, testes, lint e utilitários;
- empacotamento `.deb` e binário standalone.

Fluxo principal:

`arquivo.trm -> compilar -> arquivo.tbc -> executar`

## 2) O que você já pode fazer com a linguagem

### 2.1 Base da linguagem
- variáveis, números, texto, lógico e nulo;
- operadores aritméticos e comparação;
- `se/senão`, `enquanto`, `pare`, `continue`;
- funções e retorno (`retorne`);
- listas e mapas com indexação;
- expressões multilinha em `()`, `[]`, `{}`;
- `tente/pegue/finalmente` e `lance`;
- import de módulos Trama;
- suporte a variações sem acento em palavras-chave (`funcao/função`, `senao/senão`).

### 2.2 Assíncrono
- `assíncrona função` e `aguarde`;
- tarefas e timeout (`criar_tarefa`, `com_timeout`, `cancelar_tarefa`);
- utilitários de I/O assíncrono para arquivos.

### 2.3 Backend HTTP e realtime
- servidor HTTP nativo (`web_criar_app`, `web_rota`, `web_iniciar`, `web_parar`);
- middleware e contratos de rota;
- JWT e RBAC;
- realtime (WebSocket/fallback), salas/canais, presença, eventos e broadcast seletivo;
- base para ack/nack/retry/reenvio e compatibilidade Socket.IO mínima.

### 2.4 Banco, dados e persistência
- conexão SQL (`sqlite`, `postgres`, `postgresql`);
- executar consultas e transações;
- query builder/ORM inicial;
- migrações e sementes;
- storage local/S3 compatível;
- cache offline e sync incremental (base).

### 2.5 Segurança, observabilidade e operação
- JWT (`jwt_criar`, `jwt_verificar`);
- hash de senha e RBAC;
- logs estruturados;
- métricas e tracing;
- dashboard/alertas iniciais;
- scripts de deploy/healthcheck/smoke.

### 2.6 Tooling de linguagem
- `trama executar` (fonte `.trm`);
- `trama compilar` (gera `.tbc`);
- `trama executar-tbc`;
- `trama testar`, `trama lint`, `trama formatar`, `trama cobertura`;
- `trama template-backend`.

## 3) Estado nativo v2.0 (resumo real)

- VM nativa C já executa `.tbc`.
- Há diagnóstico de runtime (`--diagnostico-runtime`).
- Há suporte nativo para exceções, await sequencial e import `.tbc`.
- `executar`/`compilar` estão disponíveis no binário nativo por ponte standalone.
- Roadmap pós-v2.0 no README detalha evolução para maturidade máxima.

## 4) Como usar no dia a dia

### Executar um `.trm`
```bash
trama executar exemplo.trm
```

### Compilar para `.tbc`
```bash
trama compilar exemplo.trm -o exemplo.tbc
```

### Executar bytecode
```bash
trama executar-tbc exemplo.tbc
```

### Checar qualidade dos exemplos
```bash
PYTHONPATH=src .venv/bin/python -m trama.cli lint exemplos
```

## 5) Diretórios úteis

- `exemplos/`: exemplos oficiais da linguagem.
- `docs/`: documentação versionada e roadmap.
- `selfhost/`: toolchain de auto-hospedagem/compilação.
- `native/`: runtime nativo em C.
- `.local/`: área local (não versionada) para testes/manuais temporários.

## 6) Limitações práticas atuais

Para cenários enterprise de escala muito alta, ainda há evolução planejada no roadmap v2.0.1-v2.0.9 (ORM avançado, cache distribuído completo, segurança avançada, observabilidade/SRE aprofundada e runtime 100% nativo sem ponte).
Há também um roadmap detalhado de maturidade em v2.1.x, com os 7 eixos críticos e plano explícito para linguagem em codebase grande (`para/em`, módulos e tipagem gradual).

## 7) Referências rápidas

- `README.md` (estado e roadmap)
- `docs/LINGUAGEM_V2_0.md`
- `docs/MANUAL_V2_0_FASE2.md`
- `docs/V2_FASE2_PARIDADE_VM_NATIVA.md`
- `docs/ROADMAP_IMPLEMENTACOES_FUTURAS_V2_1.md`
