from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import pytest

from trama.compiler import CompileError, compile_source
from trama.vm import VMError, run_source


def _run_capture(codigo: str) -> tuple[object, list[str]]:
    out: list[str] = []
    result = run_source(codigo, print_fn=out.append)
    return result, out


def test_execucao_principal_e_exibir() -> None:
    codigo = (
        "função principal()\n"
        "    exibir(\"Olá\")\n"
        "fim\n"
    )
    result, out = _run_capture(codigo)
    assert result is None
    assert out == ["Olá"]


def test_precedencia_aritmetica() -> None:
    codigo = (
        "função principal()\n"
        "    exibir(1 + 2 * 3)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["7"]


def test_if_senao_sem_acento() -> None:
    codigo = (
        "função principal()\n"
        "    se verdadeiro\n"
        "        exibir(\"ok\")\n"
        "    senao\n"
        "        exibir(\"falha\")\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["ok"]


def test_while_com_continue_e_pare() -> None:
    codigo = (
        "função principal()\n"
        "    i = 0\n"
        "    enquanto i < 10\n"
        "        i = i + 1\n"
        "        se i == 3\n"
        "            continue\n"
        "        fim\n"
        "        se i == 5\n"
        "            pare\n"
        "        fim\n"
        "        exibir(i)\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["1", "2", "4"]


def test_funcoes_com_retorno() -> None:
    codigo = (
        "função soma(a, b)\n"
        "    retorne a + b\n"
        "fim\n"
        "função principal()\n"
        "    exibir(soma(10, 20))\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["30"]


def test_closure_funciona() -> None:
    codigo = (
        "função principal()\n"
        "    base = 10\n"
        "    função soma_local(x)\n"
        "        retorne x + base\n"
        "    fim\n"
        "    exibir(soma_local(5))\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["15"]


def test_tente_pegue_finalmente() -> None:
    codigo = (
        "função principal()\n"
        "    tente\n"
        "        lance \"erro\"\n"
        "    pegue e\n"
        "        exibir(e)\n"
        "    finalmente\n"
        "        exibir(\"fim\")\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["erro", "fim"]


def test_tente_finalmente_repropaga() -> None:
    codigo = (
        "função principal()\n"
        "    tente\n"
        "        lance \"x\"\n"
        "    finalmente\n"
        "        exibir(\"sempre\")\n"
        "    fim\n"
        "fim\n"
    )
    with pytest.raises(VMError, match="Exceção não tratada"):
        run_source(codigo)


def test_colecoes_e_json() -> None:
    codigo = (
        "função principal()\n"
        "    dados = {\"nome\": \"ana\", \"nums\": [1, 2, 3]}\n"
        "    txt = json_stringify(dados)\n"
        "    obj = json_parse(txt)\n"
        "    exibir(obj[\"nome\"])\n"
        "    exibir(obj[\"nums\"][1])\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["ana", "2"]


def test_importe_modulo(tmp_path) -> None:
    mod = tmp_path / "mathx.trm"
    mod.write_text(
        "função dobro(x)\n"
        "    retorne x * 2\n"
        "fim\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.trm"
    main.write_text(
        "importe mathx como m\n"
        "função principal()\n"
        "    exibir(m[\"dobro\"](21))\n"
        "fim\n",
        encoding="utf-8",
    )

    out: list[str] = []
    result = run_source(main.read_text(encoding="utf-8"), print_fn=out.append, source_path=str(main))
    assert result is None
    assert out == ["42"]


def test_erro_break_fora_de_laco() -> None:
    with pytest.raises(CompileError, match="dentro de laço"):
        compile_source("pare\n")


def test_erro_nome_nao_definido() -> None:
    with pytest.raises(VMError, match="Nome não definido"):
        run_source("função principal()\nexibir(x)\nfim\n")


def test_assincrona_e_aguarde_basico() -> None:
    codigo = (
        "assíncrona função dobro_async(x)\n"
        "    retorne x * 2\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    valor = aguarde dobro_async(21)\n"
        "    exibir(valor)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["42"]


def test_tarefas_timeout_cancelamento() -> None:
    codigo = (
        "assíncrona função demorado()\n"
        "    aguarde dormir(0.05)\n"
        "    retorne 99\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    t1 = criar_tarefa(demorado())\n"
        "    t2 = criar_tarefa(demorado())\n"
        "    cancelar_tarefa(t2)\n"
        "    tente\n"
        "        valor = aguarde com_timeout(t1, 1.0)\n"
        "        exibir(valor)\n"
        "    pegue erro\n"
        "        exibir(\"falhou\")\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["99"]


def test_io_nao_bloqueante(tmp_path) -> None:
    arquivo = tmp_path / "async_io.txt"
    codigo = (
        "assíncrona função principal()\n"
        f"    aguarde escrever_texto_async(\"{arquivo}\", \"ola async\")\n"
        f"    conteudo = aguarde ler_texto_async(\"{arquivo}\")\n"
        "    exibir(conteudo)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["ola async"]


def test_stdlib_fs_env_time_log(tmp_path, monkeypatch) -> None:
    arquivo = tmp_path / "sync.txt"
    monkeypatch.setenv("TRAMA_HOST", "localhost")
    monkeypatch.setenv("TRAMA_PORT", "8080")

    codigo = (
        "função principal()\n"
        f"    escrever_texto(\"{arquivo}\", \"abc\")\n"
        f"    exibir(ler_texto(\"{arquivo}\"))\n"
        f"    exibir(arquivo_existe(\"{arquivo}\"))\n"
        "    cfg = config_carregar({\"host\": \"127.0.0.1\", \"porta\": 3000}, \"TRAMA_\")\n"
        "    exibir(cfg[\"host\"])\n"
        "    exibir(cfg[\"port\"])\n"
        "    exibir(env_obter(\"TRAMA_HOST\"))\n"
        "    exibir(agora_iso() != nulo)\n"
        "    exibir(timestamp() > 0)\n"
        "    log_info(\"ok\")\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out[0:7] == ["abc", "True", "localhost", "8080", "localhost", "True", "True"]
    assert "[INFO] ok" in out[-1]


def test_json_robusto() -> None:
    codigo = (
        "função principal()\n"
        "    bom = json_parse_seguro(\"{\\\"a\\\":1}\")\n"
        "    ruim = json_parse_seguro(\"{\")\n"
        "    exibir(bom[\"ok\"])\n"
        "    exibir(ruim[\"ok\"])\n"
        "    exibir(json_stringify_pretty({\"z\": 1, \"a\": 2}) != nulo)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["True", "False", "True"]


def test_http_client_async() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        codigo = (
            "assíncrona função principal()\n"
            f"    resp = aguarde http_get(\"http://127.0.0.1:{port}/ok\")\n"
            "    exibir(resp[\"status\"])\n"
            "    exibir(resp[\"json\"][\"ok\"])\n"
            "fim\n"
        )
        _, out = _run_capture(codigo)
        assert out == ["200", "True"]
    finally:
        server.shutdown()
        server.server_close()


def test_v11_cache_resiliencia_config_segredos(monkeypatch) -> None:
    monkeypatch.setenv("TRAMA_MODO", "producao")
    codigo = (
        "assíncrona função principal()\n"
        "    contador = 0\n"
        "    função consulta()\n"
        "        contador = contador + 1\n"
        "        se contador < 3\n"
        "            lance \"transiente\"\n"
        "        fim\n"
        "        retorne \"ok\"\n"
        "    fim\n"
        "    valor = aguarde resiliencia_executar(\"svc_vm\", consulta, [], {\"tentativas\": 5, \"base_backoff_segundos\": 0, \"jitter_segundos\": 0})\n"
        "    exibir(valor)\n"
        "    exibir(circuito_status(\"svc_vm\")[\"estado\"])\n"
        "    cache_definir(\"usuario:1\", {\"nome\": \"ana\"}, 5)\n"
        "    exibir(cache_obter(\"usuario:1\")[\"nome\"])\n"
        "    cache_invalidar_padrao(\"usuario:*\")\n"
        "    exibir(cache_existe(\"usuario:1\"))\n"
        "    cfg = config_carregar_ambiente({\"modo\": \"dev\"}, \"TRAMA_\", [\"modo\"], {\"modo\": \"texto\"})\n"
        "    exibir(cfg[\"modo\"])\n"
        "    exibir(segredo_mascarar(\"abcdef\", 2))\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out[0:5] == ["ok", "fechado", "ana", "False", "producao"]
    assert out[5].endswith("ef")


def test_v12_storage_media_local(tmp_path) -> None:
    storage_dir = tmp_path / "storage"
    codigo = (
        "função principal()\n"
        f"    s = armazenamento_criar_local(\"{storage_dir}\")\n"
        "    compactado = midia_comprimir_gzip(\"ola mundo\", 6)\n"
        "    r1 = armazenamento_salvar(s, \"docs/a.txt.gz\", compactado, \"application/gzip\", {\"origem\": \"teste\"})\n"
        "    exibir(r1[\"ok\"])\n"
        "    r2 = armazenamento_ler(s, \"docs/a.txt.gz\")\n"
        "    exibir(r2[\"size\"] > 0)\n"
        "    texto = midia_descomprimir_gzip(r2[\"bytes\"])\n"
        "    exibir(texto)\n"
        "    exibir(armazenamento_listar(s, \"docs\")[0])\n"
        "    exibir(armazenamento_remover(s, \"docs/a.txt.gz\"))\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["True", "True", "b'ola mundo'", "docs/a.txt.gz", "True"]


def test_web_server_nativo_rotas_validacao_cors_health_static(tmp_path) -> None:
    static_dir = tmp_path / "publico"
    static_dir.mkdir(parents=True, exist_ok=True)
    (static_dir / "hello.txt").write_text("conteudo-estatico", encoding="utf-8")

    codigo = (
        "assíncrona função principal()\n"
        "    app = web_criar_app()\n"
        "    web_adicionar_rota_json(app, \"GET\", \"/ola\", {\"mensagem\": \"ok\"}, 200)\n"
        "    web_adicionar_rota_echo_json(app, \"POST\", \"/echo\", [\"nome\"])\n"
        "    web_usar_middleware(app, \"request_id\")\n"
        "    web_configurar_cors(app, \"*\")\n"
        "    web_ativar_healthcheck(app, \"/healthz\")\n"
        f"    web_servir_estaticos(app, \"/static\", \"{static_dir}\")\n"
        "    servidor = aguarde web_iniciar(app, \"127.0.0.1\", 0)\n"
        "    base = servidor[\"base_url\"]\n"
        "    r1 = aguarde http_get(base + \"/ola\")\n"
        "    exibir(r1[\"status\"])\n"
        "    exibir(r1[\"json\"][\"ok\"])\n"
        "    exibir(r1[\"json\"][\"dados\"][\"mensagem\"])\n"
        "    exibir(r1[\"headers\"][\"Access-Control-Allow-Origin\"])\n"
        "    exibir(r1[\"headers\"][\"X-Request-Id\"] != nulo)\n"
        "    r2 = aguarde http_post(base + \"/echo\", {\"nome\": \"trama\"}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(r2[\"status\"])\n"
        "    exibir(r2[\"json\"][\"ok\"])\n"
        "    exibir(r2[\"json\"][\"dados\"][\"payload\"][\"nome\"])\n"
        "    r3 = aguarde http_post(base + \"/echo\", {\"x\": 1}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(r3[\"status\"])\n"
        "    exibir(r3[\"json\"][\"erro\"][\"codigo\"])\n"
        "    r4 = aguarde http_get(base + \"/healthz\")\n"
        "    exibir(r4[\"status\"])\n"
        "    exibir(r4[\"json\"][\"status\"])\n"
        "    r5 = aguarde http_get(base + \"/static/hello.txt\")\n"
        "    exibir(r5[\"status\"])\n"
        "    exibir(r5[\"corpo\"])\n"
        "    aguarde web_parar(servidor)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == [
        "200",
        "True",
        "ok",
        "*",
        "True",
        "200",
        "True",
        "trama",
        "422",
        "VALIDACAO_FALHOU",
        "200",
        "up",
        "200",
        "conteudo-estatico",
    ]


def test_v06_db_driver_query_builder_transacoes_migracoes_seed(tmp_path) -> None:
    db_file = tmp_path / "trama_v06.db"
    codigo = (
        "assíncrona função principal()\n"
        f"    conn = aguarde pg_conectar(\"sqlite:///{db_file}\")\n"
        "    aguarde pg_executar(conn, \"CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, ativo INTEGER)\")\n"
        "    q = qb_select(\"usuarios\", [\"id\", \"nome\"]) \n"
        "    q = qb_where_eq(q, \"nome\", \"ana\")\n"
        "    q = qb_order_by(q, \"id\", \"DESC\")\n"
        "    q = qb_limite(q, 10)\n"
        "    exibir(qb_sql(q)[\"sql\"] != nulo)\n"
        "    m1 = aguarde migracao_aplicar(conn, \"001_posts\", \"CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT);\")\n"
        "    m2 = aguarde migracao_aplicar(conn, \"001_posts\", \"CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT);\")\n"
        "    exibir(m1[\"aplicada\"])\n"
        "    exibir(m2[\"aplicada\"])\n"
        "    s1 = aguarde seed_aplicar(conn, \"seed_ana\", \"INSERT INTO usuarios (nome, ativo) VALUES ('ana', 1);\")\n"
        "    s2 = aguarde seed_aplicar(conn, \"seed_ana\", \"INSERT INTO usuarios (nome, ativo) VALUES ('ana', 1);\")\n"
        "    exibir(s1[\"aplicada\"])\n"
        "    exibir(s2[\"aplicada\"])\n"
        "    tx = aguarde pg_transacao_iniciar(conn)\n"
        "    aguarde pg_tx_executar(tx, \"INSERT INTO usuarios (nome, ativo) VALUES (?, ?)\", [\"bia\", 1])\n"
        "    dentro_tx = aguarde pg_tx_consultar(tx, \"SELECT COUNT(*) AS c FROM usuarios\")\n"
        "    exibir(dentro_tx[0][\"c\"] >= 2)\n"
        "    aguarde pg_transacao_rollback(tx)\n"
        "    apos_rb = aguarde pg_consultar(conn, \"SELECT COUNT(*) AS c FROM usuarios\")\n"
        "    exibir(apos_rb[0][\"c\"] >= 1)\n"
        "    tx2 = aguarde pg_transacao_iniciar(conn)\n"
        "    aguarde pg_tx_executar(tx2, \"INSERT INTO usuarios (nome, ativo) VALUES (?, ?)\", [\"caique\", 1])\n"
        "    aguarde pg_transacao_commit(tx2)\n"
        "    apos_commit = aguarde pg_consultar(conn, \"SELECT COUNT(*) AS c FROM usuarios\")\n"
        "    exibir(apos_commit[0][\"c\"] >= 2)\n"
        "    novo_id = aguarde orm_inserir(conn, \"usuarios\", {\"nome\": \"dora\", \"ativo\": 1})\n"
        "    u1 = aguarde orm_buscar_por_id(conn, \"usuarios\", novo_id)\n"
        "    exibir(u1[\"nome\"])\n"
        "    aguarde orm_atualizar(conn, \"usuarios\", {\"nome\": \"dora2\"}, {\"id\": novo_id})\n"
        "    u2 = aguarde orm_buscar_por_id(conn, \"usuarios\", novo_id)\n"
        "    exibir(u2[\"nome\"])\n"
        "    aguarde pg_fechar(conn)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == [
        "True",
        "True",
        "False",
        "True",
        "False",
        "True",
        "True",
        "True",
        "dora",
        "dora2",
    ]


def test_v06_aliases_ptbr_banco(tmp_path) -> None:
    db_file = tmp_path / "trama_v06_ptbr.db"
    codigo = (
        "assíncrona função principal()\n"
        f"    conn = aguarde banco_conectar(\"sqlite:///{db_file}\")\n"
        "    aguarde banco_executar(conn, \"CREATE TABLE IF NOT EXISTS itens (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)\")\n"
        "    id = aguarde modelo_inserir(conn, \"itens\", {\"nome\": \"ptbr\"})\n"
        "    q = consulta_selecionar(\"itens\", [\"id\", \"nome\"]) \n"
        "    q = consulta_onde_igual(q, \"id\", id)\n"
        "    rows = aguarde consulta_executar(conn, q)\n"
        "    exibir(rows[0][\"nome\"])\n"
        "    tx = aguarde transacao_iniciar(conn)\n"
        "    aguarde transacao_executar(tx, \"INSERT INTO itens (nome) VALUES (?)\", [\"extra\"])\n"
        "    aguarde transacao_confirmar(tx)\n"
        "    mig = aguarde migracao_aplicar(conn, \"001_exemplo\", \"CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY AUTOINCREMENT);\")\n"
        "    sem = aguarde semente_aplicar(conn, \"seed_exemplo\", \"INSERT INTO itens (nome) VALUES ('s1');\")\n"
        "    exibir(mig[\"aplicada\"])\n"
        "    exibir(sem[\"aplicada\"])\n"
        "    aguarde banco_fechar(conn)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["ptbr", "True", "True"]


def test_v07_auth_jwt_hash_rbac() -> None:
    codigo = (
        "função principal()\n"
        "    h = senha_hash(\"abc123\", \"pbkdf2\")\n"
        "    exibir(senha_verificar(\"abc123\", h))\n"
        "    tok = jwt_criar({\"sub\": \"u1\", \"papel\": \"admin\"}, \"segredo\", 60)\n"
        "    dados = jwt_verificar(tok, \"segredo\")\n"
        "    exibir(dados[\"sub\"])\n"
        "    modelo = rbac_criar({\"admin\": [\"users:write\"], \"viewer\": [\"users:read\"]}, {\"admin\": [\"viewer\"]})\n"
        "    usuarios = {}\n"
        "    usuarios = rbac_atribuir(usuarios, \"u1\", \"admin\")\n"
        "    exibir(rbac_tem_papel(usuarios, \"u1\", \"admin\"))\n"
        "    exibir(rbac_tem_permissao(modelo, usuarios, \"u1\", \"users:read\"))\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["True", "u1", "True", "True"]


def test_v08_observabilidade_logs_metricas_tracing() -> None:
    codigo = (
        "função principal()\n"
        "    metricas_reset()\n"
        "    tracos_reset()\n"
        "    metrica_incrementar(\"http_requests_total\", 1, {\"rota\": \"/health\"})\n"
        "    metrica_observar(\"http_latencia_ms\", 12.5, {\"rota\": \"/health\"})\n"
        "    m = metricas_snapshot()\n"
        "    exibir(m[\"counters\"][0][\"nome\"])\n"
        "    s = traco_iniciar(\"req\", {\"metodo\": \"GET\"})\n"
        "    traco_evento(s, \"db.query\", {\"ok\": verdadeiro})\n"
        "    sf = traco_finalizar(s, \"ok\")\n"
        "    t = tracos_snapshot()\n"
        "    exibir(sf[\"status\"])\n"
        "    exibir(t[\"spans\"][0][\"nome\"])\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["http_requests_total", "ok", "req"]


def test_v10_http_programavel_middleware_schema_auth_rate_limit() -> None:
    codigo = (
        "função pre(req)\n"
        "    se req[\"consulta\"][\"bloq\"] == \"1\"\n"
        "        retorne {\"parar\": verdadeiro, \"resposta\": {\"status\": 403, \"json\": {\"ok\": falso, \"erro\": \"BLOQUEADO\"}}}\n"
        "    fim\n"
        "    retorne {\"parar\": falso}\n"
        "fim\n"
        "função item(req)\n"
        "    retorne {\"status\": 200, \"json\": {\"ok\": verdadeiro, \"id\": req[\"parametros\"][\"id\"]}}\n"
        "fim\n"
        "função criar(req)\n"
        "    retorne {\"status\": 201, \"json\": {\"ok\": verdadeiro, \"nome\": req[\"corpo\"][\"nome\"]}}\n"
        "fim\n"
        "função privado(req)\n"
        "    retorne {\"status\": 200, \"json\": {\"ok\": verdadeiro, \"sub\": req[\"usuario\"][\"sub\"]}}\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    app = web_criar_app()\n"
        "    versao = web_api_versionar(app, \"v1\")\n"
        "    web_saude_paths(app, \"/saude\", \"/pronto\", \"/vivo\")\n"
        "    web_middleware(app, pre, \"pre\")\n"
        "    web_rota(app, \"GET\", versao + \"/itens/:id\", item)\n"
        "    web_rota(app, \"POST\", versao + \"/itens\", criar, {\"corpo_obrigatorio\": [\"nome\"]})\n"
        "    segredo = \"segredo-123\"\n"
        "    web_rota(app, \"GET\", versao + \"/privado\", privado, nulo, {\"jwt_segredo\": segredo, \"rbac_permissoes\": [\"admin:ler\"]})\n"
        "    web_rate_limit(app, 1, 60, versao + \"/limitado/abc\", \"GET\")\n"
        "    web_rota(app, \"GET\", versao + \"/limitado/:id\", item)\n"
        "    servidor = aguarde web_iniciar(app, \"127.0.0.1\", 0)\n"
        "    base = servidor[\"base_url\"]\n"
        "    r1 = aguarde http_get(base + versao + \"/itens/10?bloq=0\")\n"
        "    exibir(r1[\"status\"])\n"
        "    exibir(r1[\"json\"][\"id\"])\n"
        "    r2 = aguarde http_get(base + versao + \"/itens/10?bloq=1\")\n"
        "    exibir(r2[\"status\"])\n"
        "    r3 = aguarde http_post(base + versao + \"/itens?bloq=0\", {\"x\": 1}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(r3[\"status\"])\n"
        "    r4 = aguarde http_post(base + versao + \"/itens?bloq=0\", {\"nome\": \"ana\"}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(r4[\"status\"])\n"
        "    token = token_criar({\"sub\": \"u1\", \"permissoes\": [\"admin:ler\"]}, segredo, 60)\n"
        "    r5 = aguarde http_get(base + versao + \"/privado?bloq=0\", {\"Authorization\": \"Bearer \" + token})\n"
        "    exibir(r5[\"status\"])\n"
        "    exibir(r5[\"json\"][\"sub\"])\n"
        "    r6 = aguarde http_get(base + versao + \"/limitado/abc?bloq=0\")\n"
        "    r7 = aguarde http_get(base + versao + \"/limitado/abc?bloq=0\")\n"
        "    exibir(r6[\"status\"])\n"
        "    exibir(r7[\"status\"])\n"
        "    s1 = aguarde http_get(base + \"/saude\")\n"
        "    s2 = aguarde http_get(base + \"/pronto\")\n"
        "    s3 = aguarde http_get(base + \"/vivo\")\n"
        "    exibir(s1[\"json\"][\"status\"])\n"
        "    exibir(s2[\"json\"][\"status\"])\n"
        "    exibir(s3[\"json\"][\"status\"])\n"
        "    aguarde web_parar(servidor)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["200", "10", "403", "422", "201", "200", "u1", "200", "429", "up", "ready", "alive"]


def test_v10_contrato_api_versionado() -> None:
    codigo = (
        "função ok(req)\n"
        "    retorne {\"status\": 200, \"json\": {\"ok\": verdadeiro, \"dados\": {\"id\": 1}, \"erro\": nulo, \"meta\": {\"v\": 1}}}\n"
        "fim\n"
        "função ruim(req)\n"
        "    retorne {\"status\": 200, \"json\": {\"ok\": verdadeiro}}\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    app = web_criar_app()\n"
        "    c = {\"envelope\": verdadeiro}\n"
        "    web_rota_contrato(app, \"GET\", \"/api/v1/ok\", ok, \"v1\", c)\n"
        "    web_rota_contrato(app, \"GET\", \"/api/v1/ruim\", ruim, \"v1\", c)\n"
        "    s = aguarde web_iniciar(app, \"127.0.0.1\", 0)\n"
        "    b = s[\"base_url\"]\n"
        "    r1 = aguarde http_get(b + \"/api/v1/ok\")\n"
        "    r2 = aguarde http_get(b + \"/api/v1/ruim\")\n"
        "    exibir(r1[\"status\"])\n"
        "    exibir(r2[\"status\"])\n"
        "    exibir(r2[\"json\"][\"erro\"][\"codigo\"])\n"
        "    aguarde web_parar(s)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["200", "500", "CONTRATO_INVALIDO"]


def test_v10_jobs_fila_retry_idempotencia() -> None:
    codigo = (
        "função job(payload)\n"
        "    retorne payload[\"x\"] * 2\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    fila = fila_criar(\"emails\")\n"
        "    a = aguarde fila_enfileirar(fila, job, {\"x\": 21}, 2, 2.0, \"id-1\")\n"
        "    b = aguarde fila_enfileirar(fila, job, {\"x\": 21}, 2, 2.0, \"id-1\")\n"
        "    r = aguarde fila_processar(fila)\n"
        "    s = fila_status(fila)\n"
        "    exibir(a[\"enfileirado\"])\n"
        "    exibir(b[\"idempotente\"])\n"
        "    exibir(r[\"concluidos\"])\n"
        "    exibir(s[\"pendentes\"])\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["True", "True", "1", "0"]


def test_v10_migracao_versionada_e_rollback(tmp_path) -> None:
    db_file = tmp_path / "trama_v10.db"
    codigo = (
        "assíncrona função principal()\n"
        f"    conn = aguarde banco_conectar(\"sqlite:///{db_file}\")\n"
        "    a1 = aguarde migracao_versionada_aplicar(conn, \"001\", \"criar_t\", \"CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY);\", \"DROP TABLE IF EXISTS t;\")\n"
        "    a2 = aguarde migracao_versionada_aplicar(conn, \"001\", \"criar_t\", \"CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY);\", \"DROP TABLE IF EXISTS t;\")\n"
        "    exibir(a1[\"aplicada\"])\n"
        "    exibir(a2[\"aplicada\"])\n"
        "    st = aguarde migracao_listar(conn)\n"
        "    exibir(st[0][\"versao\"])\n"
        "    rv = aguarde migracao_desfazer_ultima(conn)\n"
        "    exibir(rv[\"revertida\"])\n"
        "    cnt = aguarde banco_consultar(conn, \"SELECT COUNT(*) AS c FROM _trama_migration_versions\")\n"
        "    exibir(cnt[0][\"c\"])\n"
        "    aguarde banco_fechar(conn)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["True", "False", "001", "True", "0"]


def test_v10_migracao_dry_run_e_compatibilidade(tmp_path) -> None:
    db_file = tmp_path / "trama_v10_dry.db"
    codigo = (
        "assíncrona função principal()\n"
        f"    conn = aguarde banco_conectar(\"sqlite:///{db_file}\")\n"
        "    d = aguarde migracao_versionada_aplicar(conn, \"010\", \"dry\", \"CREATE TABLE IF NOT EXISTS dry_t (id INTEGER PRIMARY KEY);\", \"DROP TABLE IF EXISTS dry_t;\", verdadeiro)\n"
        "    exibir(d[\"dry_run\"])\n"
        "    st = aguarde migracao_listar(conn)\n"
        "    exibir(st == [])\n"
        "    a = aguarde migracao_versionada_aplicar(conn, \"011\", \"real\", \"CREATE TABLE IF NOT EXISTS real_t (id INTEGER PRIMARY KEY);\", \"DROP TABLE IF EXISTS real_t;\")\n"
        "    exibir(a[\"aplicada\"])\n"
        "    c1 = aguarde migracao_compatibilidade_validar(conn, \"011\", \"CREATE TABLE IF NOT EXISTS real_t (id INTEGER PRIMARY KEY);\")\n"
        "    exibir(c1[\"ok\"])\n"
        "    c2 = aguarde migracao_compatibilidade_validar(conn, \"011\", \"CREATE TABLE IF NOT EXISTS real_t (id INTEGER PRIMARY KEY, x TEXT);\")\n"
        "    exibir(c2[\"ok\"])\n"
        "    aguarde banco_fechar(conn)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["True", "True", "True", "True", "False"]


def test_v10_carga_basica_http() -> None:
    codigo = (
        "função ping(req)\n"
        "    retorne {\"status\": 200, \"json\": {\"ok\": verdadeiro}}\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    app = web_criar_app()\n"
        "    p = web_api_versionar(app, \"v1\")\n"
        "    web_rota(app, \"GET\", p + \"/ping\", ping)\n"
        "    servidor = aguarde web_iniciar(app, \"127.0.0.1\", 0)\n"
        "    base = servidor[\"base_url\"]\n"
        "    i = 0\n"
        "    ok = verdadeiro\n"
        "    enquanto i < 30\n"
        "        r = aguarde http_get(base + p + \"/ping\")\n"
        "        se r[\"status\"] != 200\n"
        "            ok = falso\n"
        "        fim\n"
        "        i = i + 1\n"
        "    fim\n"
        "    exibir(ok)\n"
        "    aguarde web_parar(servidor)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["True"]


def test_v14_observabilidade_correlacao_dashboard_alertas() -> None:
    codigo = (
        "função publico(req)\n"
        "    retorne {\"status\": 200, \"json\": {\"ok\": verdadeiro, \"id_requisicao\": req[\"id_requisicao\"], \"request_id\": req[\"request_id\"], \"id_traco\": req[\"id_traco\"], \"trace_id\": req[\"trace_id\"]}}\n"
        "fim\n"
        "função privado(req)\n"
        "    retorne {\"status\": 200, \"json\": {\"ok\": verdadeiro, \"id_usuario\": req[\"id_usuario\"], \"user_id\": req[\"user_id\"]}}\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    metricas_reset()\n"
        "    tracos_reset()\n"
        "    app = web_criar_app()\n"
        "    web_usar_middleware(app, \"request_id\")\n"
        "    web_ativar_observabilidade(app, \"/observabilidade\", \"/alertas\", {\"erro_percentual_limite\": 0.1, \"latencia_ms_limite\": 0.001, \"requisicoes_minimas\": 1})\n"
        "    segredo = \"seg-v14\"\n"
        "    web_rota(app, \"GET\", \"/publico\", publico)\n"
        "    web_rota(app, \"GET\", \"/privado\", privado, nulo, {\"jwt_segredo\": segredo})\n"
        "    s = aguarde web_iniciar(app, \"127.0.0.1\", 0)\n"
        "    b = s[\"base_url\"]\n"
        "    r1 = aguarde http_get(b + \"/publico\")\n"
        "    exibir(r1[\"status\"])\n"
        "    exibir(r1[\"json\"][\"id_requisicao\"] == r1[\"json\"][\"request_id\"])\n"
        "    exibir(r1[\"json\"][\"id_traco\"] == r1[\"json\"][\"trace_id\"])\n"
        "    exibir(r1[\"headers\"][\"X-Request-Id\"] == r1[\"headers\"][\"X-Id-Requisicao\"])\n"
        "    exibir(r1[\"headers\"][\"X-Trace-Id\"] == r1[\"headers\"][\"X-Id-Traco\"])\n"
        "    tok = token_criar({\"sub\": \"u42\"}, segredo, 60)\n"
        "    r2 = aguarde http_get(b + \"/privado\", {\"Authorization\": \"Bearer \" + tok})\n"
        "    exibir(r2[\"json\"][\"id_usuario\"])\n"
        "    exibir(r2[\"json\"][\"user_id\"])\n"
        "    obs = aguarde http_get(b + \"/observabilidade\")\n"
        "    exibir(obs[\"status\"])\n"
        "    exibir(obs[\"json\"][\"estado\"] != nulo)\n"
        "    exibir(obs[\"json\"][\"metricas\"][\"counters\"] != [])\n"
        "    al = aguarde http_get(b + \"/alertas\")\n"
        "    exibir(al[\"status\"])\n"
        "    exibir(al[\"json\"][\"alertas\"][\"estado\"] == \"degradado\")\n"
        "    aguarde web_parar(s)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == [
        "200",
        "True",
        "True",
        "True",
        "True",
        "u42",
        "u42",
        "200",
        "True",
        "True",
        "200",
        "True",
    ]


def test_v13_tempo_real_fallback_ptbr() -> None:
    codigo = (
        "função chat(req)\n"
        "    se req[\"evento\"] == \"mensagem\"\n"
        "        se req[\"mensagem\"][\"tipo\"] == \"chat\"\n"
        "            retorne {\"destino\": \"sala\", \"sala\": \"lobby\", \"evento\": \"chat_msg\", \"dados\": {\"txt\": req[\"mensagem\"][\"txt\"]}}\n"
        "        fim\n"
        "    fim\n"
        "    retorne {\"aceitar\": verdadeiro}\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    app = web_criar_app()\n"
        "    web_tempo_real_rota(app, \"/ws/chat\", chat, {\"jwt_segredo\": \"seg-v13\"})\n"
        "    web_tempo_real_ativar_fallback(app, \"/tempo-real/fallback\", 0.5)\n"
        "    web_tempo_real_definir_limites(app, {\"max_conexoes_por_ip\": 5, \"max_mensagens_por_janela\": 10, \"janela_rate_segundos\": 5})\n"
        "    s = aguarde web_iniciar(app, \"127.0.0.1\", 0)\n"
        "    b = s[\"base_url\"]\n"
        "    tok = token_criar({\"sub\": \"u1\"}, \"seg-v13\", 60)\n"
        "    c = aguarde http_post(b + \"/tempo-real/fallback/conectar?token=\" + tok, {\"canal\": \"/ws/chat\"}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(c[\"status\"])\n"
        "    idc = c[\"json\"][\"id_conexao\"]\n"
        "    e1 = aguarde http_post(b + \"/tempo-real/fallback/enviar\", {\"id_conexao\": idc, \"mensagem\": {\"tipo\": \"entrar_sala\", \"sala\": \"lobby\"}}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(e1[\"status\"])\n"
        "    e2 = aguarde http_post(b + \"/tempo-real/fallback/enviar\", {\"id_conexao\": idc, \"mensagem\": {\"tipo\": \"chat\", \"txt\": \"ola\"}}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(e2[\"status\"])\n"
        "    r = aguarde http_get(b + \"/tempo-real/fallback/receber?id_conexao=\" + idc + \"&timeout_segundos=0.2\")\n"
        "    exibir(r[\"status\"])\n"
        "    exibir(r[\"json\"][\"ok\"])\n"
        "    exibir(tamanho(r[\"json\"][\"eventos\"]) > 0)\n"
        "    st = web_tempo_real_status(app, \"/ws/chat\")\n"
        "    exibir(st[\"canais\"][0][\"conexoes_ativas\"] >= 1)\n"
        "    ds = aguarde http_post(b + \"/tempo-real/fallback/desconectar\", {\"id_conexao\": idc}, {\"Content-Type\": \"application/json\"})\n"
        "    exibir(ds[\"status\"])\n"
        "    aguarde web_parar(s)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["200", "200", "200", "200", "True", "True", "True", "200"]


def test_parser_multilinha_chamada_lista_mapa() -> None:
    codigo = (
        "função soma(a, b)\n"
        "    retorne a + b\n"
        "fim\n"
        "função principal()\n"
        "    valores = [\n"
        "        1,\n"
        "        2,\n"
        "        3\n"
        "    ]\n"
        "    cfg = {\n"
        "        \"nome\": \"trama\",\n"
        "        \"nums\": [\n"
        "            10,\n"
        "            20\n"
        "        ]\n"
        "    }\n"
        "    total = soma(\n"
        "        valores[0],\n"
        "        cfg[\"nums\"][1]\n"
        "    )\n"
        "    exibir(total)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["21"]


def test_parser_multilinha_encadeado_com_quebra_controlada() -> None:
    codigo = (
        "função principal()\n"
        "    dados = {\n"
        "        \"a\": {\n"
        "            \"b\": [\n"
        "                {\"x\": 7}\n"
        "            ]\n"
        "        }\n"
        "    }\n"
        "    exibir(\n"
        "        dados\n"
        "        [\"a\"]\n"
        "        [\"b\"]\n"
        "        [0]\n"
        "        [\"x\"]\n"
        "    )\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["7"]


def test_parser_multilinha_erro_virgula_faltando() -> None:
    codigo = (
        "função principal()\n"
        "    xs = [\n"
        "        1\n"
        "        2\n"
        "    ]\n"
        "fim\n"
    )
    with pytest.raises(Exception, match="Esperado '\\]' no literal de lista"):
        compile_source(codigo)


def test_parser_multilinha_erro_delimitador_nao_fechado() -> None:
    codigo = (
        "função principal()\n"
        "    cfg = {\n"
        "        \"a\": 1,\n"
        "        \"b\": 2\n"
        "fim\n"
    )
    with pytest.raises(Exception, match="Esperado '\\}' no literal de mapa"):
        compile_source(codigo)
