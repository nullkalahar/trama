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
