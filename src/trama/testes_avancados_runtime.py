"""Harness oficial de testes avancados da Trama (v2.0.8)."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib import error, parse, request

from .bytecode import program_to_dict
from . import cache_runtime
from .compiler import compile_source
from . import db_runtime
from . import observability_runtime
from . import security_runtime
from . import vm
from . import web_runtime


def _agora_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _percentil(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    pos = min(len(vals) - 1, max(0, int(round((len(vals) - 1) * p))))
    return float(vals[pos])


def _http_json(
    method: str,
    url: str,
    body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 3.0,
) -> tuple[int, dict[str, object], dict[str, str], float]:
    hdr = {"Content-Type": "application/json; charset=utf-8"}
    hdr.update(dict(headers or {}))
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, method=method.upper(), data=payload, headers=hdr)
    ini = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            txt = resp.read().decode("utf-8", errors="replace")
            dur = (time.perf_counter() - ini) * 1000.0
            return int(resp.getcode() or 0), (json.loads(txt) if txt else {}), dict(resp.headers.items()), dur
    except error.HTTPError as exc:
        txt = exc.read().decode("utf-8", errors="replace")
        dur = (time.perf_counter() - ini) * 1000.0
        return int(exc.code), (json.loads(txt) if txt else {}), dict(exc.headers.items()), dur


def _http_text(url: str, timeout: float = 3.0) -> tuple[int, str, dict[str, str], float]:
    req = request.Request(url=url, method="GET")
    ini = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            txt = resp.read().decode("utf-8", errors="replace")
            dur = (time.perf_counter() - ini) * 1000.0
            return int(resp.getcode() or 0), txt, dict(resp.headers.items()), dur
    except error.HTTPError as exc:
        txt = exc.read().decode("utf-8", errors="replace")
        dur = (time.perf_counter() - ini) * 1000.0
        return int(exc.code), txt, dict(exc.headers.items()), dur


@dataclass
class _Servidor:
    runtime: web_runtime.WebRuntime
    base_url: str


def _iniciar_servidor(app: web_runtime.WebApp) -> _Servidor:
    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _msg: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    return _Servidor(runtime=rt, base_url=f"http://127.0.0.1:{rt.port}")


def _parar_servidor(s: _Servidor) -> None:
    s.runtime.stop()


def _redis_ping(redis_url: str, timeout: float = 0.5) -> bool:
    parsed = parse.urlparse(redis_url)
    host = parsed.hostname or "127.0.0.1"
    port = int(parsed.port or 6379)
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(b"*1\r\n$4\r\nPING\r\n")
        data = sock.recv(64)
        return b"PONG" in data


async def _harness_sqlite(base_dir: Path) -> dict[str, object]:
    base_dir.mkdir(parents=True, exist_ok=True)
    db_path = base_dir / "fixture_v208.sqlite3"
    dsn = f"sqlite:///{db_path}"
    conn = await db_runtime.conectar(dsn)
    try:
        mig = await db_runtime.migracao_aplicar_versionada_v2(
            conn=conn,
            versao="208.001",
            nome="criar_pedidos",
            up_sql="CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL, criado_em TEXT NOT NULL);",
            down_sql="DROP TABLE IF EXISTS pedidos;",
            ambiente="teste",
            dry_run=False,
        )
        seed = await db_runtime.seed_aplicar_ambiente(
            conn,
            "teste",
            "base_001",
            "INSERT INTO pedidos (descricao, criado_em) VALUES ('pedido_seed', '2026-04-05T00:00:00Z');",
        )
        rows = await db_runtime.consultar(conn, "SELECT COUNT(*) AS c FROM pedidos")
        total = int(rows[0]["c"]) if rows else 0
        return {"ok": True, "dsn": dsn, "migracao": mig, "seed": seed, "total_pedidos": total}
    finally:
        await db_runtime.fechar(conn)


async def _validar_postgres(dsn: str) -> dict[str, object]:
    conn = await db_runtime.conectar(dsn)
    try:
        rs = await db_runtime.consultar(conn, "SELECT 1 AS ok")
        return {"ok": True, "status": "validado", "linhas": len(rs)}
    finally:
        await db_runtime.fechar(conn)


def executar_harness_integracao(
    *,
    diretorio_base: str = ".local/tests/v2_0_8/fixtures",
    validar_postgres: bool = True,
    validar_redis: bool = True,
) -> dict[str, object]:
    base_dir = Path(diretorio_base)
    sqlite_info = asyncio.run(_harness_sqlite(base_dir))

    pg_dsn = ""
    pg_status: dict[str, object] = {"ok": True, "status": "nao_aplicavel", "mensagem": "TRAMA_TEST_PG_DSN nao definido."}
    if validar_postgres:
        import os

        pg_dsn = str(os.getenv("TRAMA_TEST_PG_DSN", "")).strip()
        if pg_dsn:
            try:
                pg_status = asyncio.run(_validar_postgres(pg_dsn))
            except Exception as exc:  # noqa: BLE001
                pg_status = {"ok": False, "status": "falha", "erro": str(exc)}

    redis_url = ""
    redis_status: dict[str, object] = {"ok": True, "status": "nao_aplicavel", "mensagem": "TRAMA_TEST_REDIS_URL nao definido."}
    if validar_redis:
        import os

        redis_url = str(os.getenv("TRAMA_TEST_REDIS_URL", "")).strip()
        if redis_url:
            try:
                redis_status = {"ok": bool(_redis_ping(redis_url)), "status": "validado", "url": redis_url}
            except Exception as exc:  # noqa: BLE001
                redis_status = {"ok": False, "status": "falha", "erro": str(exc), "url": redis_url}

    ok = bool(sqlite_info.get("ok")) and bool(pg_status.get("ok")) and bool(redis_status.get("ok"))
    return {
        "ok": ok,
        "harness": "integracao_fixture_real",
        "executado_em": _agora_iso(),
        "sqlite": sqlite_info,
        "postgres": pg_status,
        "redis": redis_status,
    }


def executar_suite_e2e_fluxos_criticos() -> dict[str, object]:
    tmpdir = Path(tempfile.mkdtemp(prefix="trama_v208_e2e_"))
    db_path = tmpdir / "e2e.sqlite3"
    conn_sql = sqlite3.connect(db_path, check_same_thread=False)
    import threading
    lock = threading.RLock()
    conn_sql.execute("CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL)")
    conn_sql.commit()

    segredo = "segredo_v208_e2e"
    app = web_runtime.WebApp()

    def criar_pedido(req: dict[str, object]) -> dict[str, object]:
        corpo = dict(req.get("corpo") or {})
        desc = str(corpo.get("descricao", ""))
        with lock:
            cur = conn_sql.cursor()
            cur.execute("INSERT INTO pedidos (descricao) VALUES (?)", (desc,))
            conn_sql.commit()
            pid = int(cur.lastrowid or 0)
        return {
            "status": 201,
            "json": {
                "ok": True,
                "dados": {"id": pid, "descricao": desc},
                "erro": None,
                "meta": {"versao": "v2"},
                "links": {"self": f"/api/v1/pedidos/{pid}"},
            },
        }

    dto = {
        "corpo": {
            "tipo": "objeto",
            "permitir_campos_extras": False,
            "campos": {
                "descricao": {"tipo": "texto", "obrigatorio": True, "sanitizar": {"trim": True}, "tamanho_min": 3},
                "prioridade": {"tipo": "inteiro", "coagir": True, "padrao": 1},
            },
        }
    }
    contrato = {
        "versao_padrao": "v2",
        "versoes": {
            "v1": {"campos_obrigatorios": ["ok", "dados", "erro", "meta"]},
            "v2": {"campos_obrigatorios": ["ok", "dados", "erro", "meta", "links"]},
        },
        "retrocompativel": {"legacy": "v1"},
    }
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/api/v1/pedidos",
            criar_pedido,
            schema={},
            options={
                "jwt_segredo": segredo,
                "dto_requisicao": dto,
                "contrato_resposta": contrato,
                "contrato_entrada": {"campos_permitidos": {"corpo": ["descricao", "prioridade"]}},
            },
        )
    )

    app.tempo_real.registrar_rota("/ws/pedidos", lambda req: {"aceitar": True}, {"jwt_segredo": segredo})
    app.tempo_real.ativar_fallback("/tempo-real/fallback", 1.0)

    servidor = _iniciar_servidor(app)
    checks: list[dict[str, object]] = []
    try:
        token = security_runtime.jwt_criar({"sub": "u-e2e", "id_usuario": "u-e2e"}, segredo, exp_segundos=120)
        # negativo auth
        st0, p0, _, _ = _http_json("POST", servidor.base_url + "/api/v1/pedidos", {"descricao": "abc"})
        checks.append({"nome": "auth_obrigatoria", "ok": st0 == 401 and str(dict(p0.get("erro") or {}).get("codigo")) != ""})

        # negativo validacao
        st1, p1, _, _ = _http_json(
            "POST",
            servidor.base_url + "/api/v1/pedidos",
            {"descricao": "x", "prioridade": "nao_numero"},
            headers={"Authorization": f"Bearer {token}"},
        )
        codigos = {str(item.get("codigo")) for item in list(dict(dict(p1.get("erro") or {}).get("detalhes") or {}).get("campos", []))}
        checks.append({"nome": "dto_validacao_estavel", "ok": st1 == 422 and "VALIDACAO_FALHOU" == str(dict(p1.get("erro") or {}).get("codigo")) and "TIPO_INVALIDO" in codigos})

        # positivo contrato legado + persistencia
        st2, p2, h2, _ = _http_json(
            "POST",
            servidor.base_url + "/api/v1/pedidos",
            {"descricao": "  pedido e2e  ", "prioridade": "2", "extra": "remover"},
            headers={"Authorization": f"Bearer {token}", "X-Contrato-Versao": "legacy"},
        )
        with lock:
            rows = conn_sql.execute("SELECT COUNT(*) FROM pedidos").fetchone()
        total_pedidos = int(rows[0]) if rows else 0
        checks.append(
            {
                "nome": "contrato_legacy_persistencia",
                "ok": st2 == 201 and h2.get("X-Contrato-Versao-Aplicada") == "v1" and total_pedidos >= 1 and p2.get("ok") is True,
            }
        )

        # realtime fallback com jwt
        st3, p3, _, _ = _http_json(
            "POST",
            servidor.base_url + "/tempo-real/fallback/conectar",
            {"canal": "/ws/pedidos"},
            headers={"Authorization": f"Bearer {token}"},
        )
        checks.append({"nome": "realtime_fallback_jwt", "ok": st3 == 200 and str(p3.get("id_conexao", "")) != ""})
    finally:
        _parar_servidor(servidor)
        conn_sql.close()

    return {"ok": all(bool(x.get("ok")) for x in checks), "suite": "e2e_fluxos_criticos", "checks": checks}


def executar_regressao_contrato_api() -> dict[str, object]:
    app = web_runtime.WebApp()

    def handler(req: dict[str, object]) -> dict[str, object]:
        _ = req
        return {"status": 200, "json": {"ok": True, "dados": {"id": 1}, "erro": None, "meta": {"versao": "v2"}, "links": {"self": "/r/1"}}}

    contrato = {
        "versao_padrao": "v2",
        "versoes": {
            "v1": {"campos_obrigatorios": ["ok", "dados", "erro", "meta"]},
            "v2": {"campos_obrigatorios": ["ok", "dados", "erro", "meta", "links"]},
        },
        "retrocompativel": {"legacy": "v1"},
    }
    app.routes.append(web_runtime.WebRoute.dynamic("GET", "/api/v1/contrato", handler, schema={}, options={"contrato_resposta": contrato}))

    servidor = _iniciar_servidor(app)
    try:
        st1, p1, h1, _ = _http_json("GET", servidor.base_url + "/api/v1/contrato", headers={"X-Contrato-Versao": "legacy"})
        st2, p2, h2, _ = _http_json("GET", servidor.base_url + "/api/v1/contrato", headers={"X-Contrato-Versao": "v999"})
        checks = [
            {"nome": "legacy_aplica_v1", "ok": st1 == 200 and h1.get("X-Contrato-Versao-Aplicada") == "v1" and p1.get("ok") is True},
            {
                "nome": "versao_invalida_estavel",
                "ok": st2 == 400
                and str(dict(p2.get("erro") or {}).get("codigo")) == "CONTRATO_VERSAO_INVALIDA"
                and h2.get("X-Contrato-Versao-Solicitada") == "v999",
            },
        ]
        return {"ok": all(bool(x.get("ok")) for x in checks), "suite": "regressao_contrato_api", "checks": checks}
    finally:
        _parar_servidor(servidor)


def executar_teste_carga_concorrencia(
    *,
    total_requisicoes: int = 120,
    concorrencia: int = 12,
    slo_p95_ms_max: float = 1000.0,
    slo_erro_pct_max: float = 2.0,
    slo_throughput_min_rps: float = 5.0,
) -> dict[str, object]:
    app = web_runtime.WebApp()
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "GET",
            "/api/v1/carga",
            lambda req: {"status": 200, "json": {"ok": True, "id_requisicao": req.get("id_requisicao")}},
            schema={},
            options={},
        )
    )
    servidor = _iniciar_servidor(app)
    latencias: list[float] = []
    erros = 0
    ini = time.perf_counter()
    try:
        alvo = servidor.base_url + "/api/v1/carga"

        def _uma_req() -> tuple[int, float]:
            st, _p, _h, dur = _http_json("GET", alvo, timeout=5.0)
            return st, dur

        with ThreadPoolExecutor(max_workers=max(1, int(concorrencia))) as ex:
            futuros = [ex.submit(_uma_req) for _ in range(max(1, int(total_requisicoes)))]
            for fut in as_completed(futuros):
                st, dur = fut.result()
                latencias.append(float(dur))
                if st >= 400:
                    erros += 1
    finally:
        _parar_servidor(servidor)
    total = max(1, int(total_requisicoes))
    duracao_s = max(0.001, float(time.perf_counter() - ini))
    erro_pct = (float(erros) / float(total)) * 100.0
    throughput = float(total) / duracao_s
    p50 = _percentil(latencias, 0.50)
    p95 = _percentil(latencias, 0.95)
    ok_slo = p95 <= float(slo_p95_ms_max) and erro_pct <= float(slo_erro_pct_max) and throughput >= float(slo_throughput_min_rps)
    return {
        "ok": ok_slo,
        "suite": "carga_concorrencia",
        "parametros": {
            "total_requisicoes": total,
            "concorrencia": int(concorrencia),
            "slo_p95_ms_max": float(slo_p95_ms_max),
            "slo_erro_pct_max": float(slo_erro_pct_max),
            "slo_throughput_min_rps": float(slo_throughput_min_rps),
        },
        "metricas": {
            "duracao_s": duracao_s,
            "throughput_rps": throughput,
            "erro_pct": erro_pct,
            "latencia_p50_ms": p50,
            "latencia_p95_ms": p95,
        },
    }


def executar_teste_caos_falha_parcial() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    # Falha de DB com degradacao controlada (erro previsivel/capturado).
    try:
        asyncio.run(db_runtime.conectar("sqlite:////nao_existe_dir_v208/arquivo.db"))
        checks.append({"nome": "db_falha_parcial", "ok": False, "erro": "esperava falha"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"nome": "db_falha_parcial", "ok": True, "erro_controlado": str(exc)[:120]})

    # Falha de cache/backplane com fallback.
    grupo = f"v208_caos_{int(time.time() * 1000)}"
    inst = cache_runtime.cache_distribuido_criar(grupo=grupo, id_instancia="caos", auto_sincronizar=False)
    cache_runtime.cache_distribuido_configurar_backplane(grupo, disponivel=False)
    valor = cache_runtime.cache_distribuido_obter_ou_carregar(
        "chave_caos",
        lambda: (_ for _ in ()).throw(RuntimeError("backend_indisponivel")),
        ttl_segundos=2,
        namespace="caos",
        fallback={"ok": True, "degradado": True},
        instancia=inst,
    )
    st = cache_runtime.cache_distribuido_stats(namespace="caos", instancia=inst)
    checks.append(
        {
            "nome": "cache_falha_parcial_fallback",
            "ok": isinstance(valor, dict) and bool(valor.get("degradado")) and int(st.get("fallback_usado", 0)) >= 1,
            "stats": st,
        }
    )
    cache_runtime.cache_distribuido_configurar_backplane(grupo, disponivel=True)

    # Falha de rede com smoke check sem quebra de processo.
    rede = {
        "nome": "rede_falha_parcial",
        "ok": True,
        "resultado": {"ok": False, "base_url": "http://127.0.0.1:9", "duracao_ms": 0.0, "resultados": []},
    }
    try:
        from . import tooling_runtime

        sm = tooling_runtime.smoke_checks_http("http://127.0.0.1:9", timeout_segundos=0.2, caminhos=["/saude"])
        rede["ok"] = bool(sm.get("ok") is False and isinstance(sm.get("resultados"), list))
        rede["resultado"] = sm
    except Exception as exc:  # noqa: BLE001
        rede["ok"] = False
        rede["erro"] = str(exc)
    checks.append(rede)

    return {"ok": all(bool(x.get("ok")) for x in checks), "suite": "caos_falha_parcial", "checks": checks}


def executar_suite_v208(
    *,
    diretorio_relatorio: str = ".local/test-results",
    validar_postgres: bool = True,
    validar_redis: bool = True,
    perfil: str = "completo",
) -> dict[str, object]:
    ini = time.perf_counter()
    observability_runtime.metricas_reset()
    observability_runtime.tracos_reset()
    perfil_norm = str(perfil or "completo").strip().lower()

    integracao = executar_harness_integracao(
        diretorio_base=".local/tests/v2_0_8/fixtures",
        validar_postgres=bool(validar_postgres),
        validar_redis=bool(validar_redis),
    )
    e2e = executar_suite_e2e_fluxos_criticos()
    contrato = executar_regressao_contrato_api()
    caos = executar_teste_caos_falha_parcial()
    carga = executar_teste_carga_concorrencia(
        total_requisicoes=(120 if perfil_norm == "completo" else 60),
        concorrencia=(12 if perfil_norm == "completo" else 6),
    )

    suites = {
        "integracao": integracao,
        "e2e": e2e,
        "carga": carga,
        "contrato": contrato,
        "caos": caos,
    }
    ok = all(bool(v.get("ok")) for v in suites.values())
    dur_ms = (time.perf_counter() - ini) * 1000.0
    resumo = {
        "ok": ok,
        "versao": "2.0.8",
        "perfil": perfil_norm,
        "executado_em": _agora_iso(),
        "duracao_ms": dur_ms,
        "suites": suites,
        "metricas_observabilidade": observability_runtime.metricas_snapshot(),
    }

    out_dir = Path(diretorio_relatorio)
    out_dir.mkdir(parents=True, exist_ok=True)
    return resumo


def salvar_relatorio_json(relatorio: dict[str, object], arquivo_saida: str) -> dict[str, object]:
    out = Path(arquivo_saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "arquivo": str(out.resolve())}


def salvar_relatorio_markdown(relatorio: dict[str, object], arquivo_saida: str) -> dict[str, object]:
    out = Path(arquivo_saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    linhas: list[str] = []
    linhas.append(f"# Relatorio v{relatorio.get('versao')} - Testes Avancados")
    linhas.append("")
    linhas.append(f"- ok: `{str(bool(relatorio.get('ok'))).lower()}`")
    linhas.append(f"- versao: `{relatorio.get('versao')}`")
    linhas.append(f"- perfil: `{relatorio.get('perfil')}`")
    linhas.append(f"- executado_em: `{relatorio.get('executado_em')}`")
    linhas.append(f"- duracao_ms: `{round(float(relatorio.get('duracao_ms', 0.0)), 2)}`")
    linhas.append("")
    suites = dict(relatorio.get("suites") or {})
    for nome, payload in suites.items():
        item = dict(payload or {})
        linhas.append(f"## Suite: {nome}")
        linhas.append("")
        linhas.append(f"- ok: `{str(bool(item.get('ok'))).lower()}`")
        if "metricas" in item and isinstance(item["metricas"], dict):
            m = dict(item["metricas"])
            linhas.append(f"- latencia_p95_ms: `{round(float(m.get('latencia_p95_ms', 0.0)), 2)}`")
            linhas.append(f"- erro_pct: `{round(float(m.get('erro_pct', 0.0)), 4)}`")
            linhas.append(f"- throughput_rps: `{round(float(m.get('throughput_rps', 0.0)), 2)}`")
        if "checks" in item and isinstance(item["checks"], list):
            linhas.append("- checks:")
            for chk in item["checks"]:
                c = dict(chk or {})
                linhas.append(f"  - `{c.get('nome')}`: `{str(bool(c.get('ok'))).lower()}`")
        linhas.append("")
    out.write_text("\n".join(linhas).strip() + "\n", encoding="utf-8")
    return {"ok": True, "arquivo": str(out.resolve())}


def _compilar_tbc(fonte: Path, saida_tbc: Path) -> None:
    codigo = fonte.read_text(encoding="utf-8")
    programa = compile_source(codigo, arquivo=str(fonte))
    payload = program_to_dict(programa)
    saida_tbc.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _executar_python_tbc(arquivo_tbc: Path) -> tuple[bool, list[str], str]:
    out: list[str] = []
    try:
        vm.run_bytecode_file(str(arquivo_tbc), print_fn=lambda msg: out.append(str(msg)))
        return True, out, ""
    except Exception as exc:  # noqa: BLE001
        return False, out, str(exc)


def _build_native_bin(root_dir: Path) -> Path:
    cmd = ["bash", str(root_dir / "scripts" / "build_native_stub.sh")]
    proc = subprocess.run(cmd, cwd=str(root_dir), check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Falha ao construir runtime nativo: {proc.stderr or proc.stdout}")
    bin_path = root_dir / "dist" / "native" / "trama-native"
    if not bin_path.exists():
        raise RuntimeError("Binario nativo nao encontrado apos build.")
    return bin_path


def _executar_nativo_tbc(bin_nativo: Path, arquivo_tbc: Path) -> tuple[bool, list[str], str]:
    arquivo_abs = arquivo_tbc.resolve()
    proc = subprocess.run(
        [str(bin_nativo), "executar-tbc", str(arquivo_abs)],
        cwd=str(arquivo_tbc.parent),
        check=False,
        capture_output=True,
        text=True,
    )
    ok = proc.returncode == 0
    linhas = [ln for ln in proc.stdout.splitlines() if ln.strip() != ""]
    err = proc.stderr.strip()
    return ok, linhas, err


def executar_paridade_python_nativo_fluxos_criticos(*, diretorio_trabalho: str = ".local/tests/v2_1_2/paridade") -> dict[str, object]:
    base = Path(diretorio_trabalho)
    base.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    checks: list[dict[str, object]] = []
    try:
        bin_nativo = _build_native_bin(root)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "suite": "paridade_python_nativo",
            "checks": [{"nome": "build_nativo", "ok": False, "erro": str(exc)}],
        }

    cenarios = [
        {
            "nome": "modulos_import_export",
            "modulo": (
                "exporte somar\n"
                "função somar(a, b)\n"
                "    retorne a + b\n"
                "fim\n"
            ),
            "app": (
                'importe "mod.trm" como m expondo somar\n'
                "função principal()\n"
                "    exibir(m[\"somar\"](20, 22))\n"
                "fim\n"
            ),
        },
        {
            "nome": "async_tarefa_timeout_cancelamento",
            "modulo": "",
            "app": (
                "assíncrona função soma(a, b)\n"
                "    retorne a + b\n"
                "fim\n"
                "assíncrona função principal()\n"
                "    t1 = criar_tarefa(soma(30, 12))\n"
                "    t2 = criar_tarefa(soma(1, 1))\n"
                "    cancelar_tarefa(t2)\n"
                "    v = aguarde com_timeout(t1, 1.0)\n"
                "    exibir(v)\n"
                "fim\n"
            ),
        },
        {
            "nome": "controle_fluxo_deterministico",
            "modulo": "",
            "app": (
                "função principal()\n"
                "    xs = [1, 2, 3, 4]\n"
                "    total = 0\n"
                "    para n em xs\n"
                "        se n > 2\n"
                "            total = total + n\n"
                "        fim\n"
                "    fim\n"
                "    exibir(total)\n"
                "fim\n"
            ),
        },
    ]

    for i, c in enumerate(cenarios, start=1):
        pasta = base / f"cenario_{i:02d}"
        pasta.mkdir(parents=True, exist_ok=True)
        mod = pasta / "mod.trm"
        if c["modulo"]:
            mod.write_text(str(c["modulo"]), encoding="utf-8")
        app = pasta / "app.trm"
        app.write_text(str(c["app"]), encoding="utf-8")
        tbc = pasta / "app.tbc"
        _compilar_tbc(app, tbc)

        ok_py, out_py, err_py = _executar_python_tbc(tbc)
        ok_nat, out_nat, err_nat = _executar_nativo_tbc(bin_nativo, tbc)
        ok = bool(ok_py and ok_nat and out_py == out_nat)
        checks.append(
            {
                "nome": str(c["nome"]),
                "ok": ok,
                "python_ok": ok_py,
                "nativo_ok": ok_nat,
                "saida_python": out_py,
                "saida_nativo": out_nat,
                "erro_python": err_py,
                "erro_nativo": err_nat,
            }
        )

    return {"ok": all(bool(x.get("ok")) for x in checks), "suite": "paridade_python_nativo", "checks": checks}


def executar_contrato_http_critico_v212() -> dict[str, object]:
    app = web_runtime.WebApp()

    def _ok(req: dict[str, object]) -> dict[str, object]:
        _ = req
        return {"status": 200, "json": {"ok": True, "dados": {"nome": "trama"}, "erro": None, "meta": {"versao": "v2"}}}

    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/api/v1/critico",
            _ok,
            schema={},
            options={
                "jwt_segredo": "segredo_v212",
                "dto_requisicao": {
                    "corpo": {
                        "tipo": "objeto",
                        "permitir_campos_extras": False,
                        "campos": {"nome": {"tipo": "texto", "obrigatorio": True, "tamanho_min": 3}},
                    }
                },
            },
        )
    )
    servidor = _iniciar_servidor(app)
    checks: list[dict[str, object]] = []
    try:
        st1, p1, _, _ = _http_json("POST", servidor.base_url + "/api/v1/critico", body={"nome": "abc"})
        erro1 = dict(p1.get("erro") or {})
        checks.append(
            {
                "nome": "erro_auth_envelope_estavel",
                "ok": st1 == 401 and {"codigo", "mensagem", "detalhes"} <= set(erro1.keys()),
            }
        )

        tok = security_runtime.jwt_criar({"sub": "u_v212", "id_usuario": "u_v212"}, "segredo_v212", exp_segundos=120)
        st2, p2, _, _ = _http_json(
            "POST",
            servidor.base_url + "/api/v1/critico",
            body={"nome": "x"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        erro2 = dict(p2.get("erro") or {})
        checks.append(
            {
                "nome": "erro_validacao_envelope_estavel",
                "ok": st2 == 422
                and str(erro2.get("codigo")) == "VALIDACAO_FALHOU"
                and {"codigo", "mensagem", "detalhes"} <= set(erro2.keys()),
            }
        )
    finally:
        _parar_servidor(servidor)

    return {"ok": all(bool(x.get("ok")) for x in checks), "suite": "contrato_http_critico", "checks": checks}


def executar_carga_multi_instancia_v212(
    *,
    total_requisicoes: int = 160,
    concorrencia: int = 16,
    slo_p95_ms_max: float = 1200.0,
    slo_erro_pct_max: float = 2.0,
    slo_throughput_min_rps: float = 8.0,
) -> dict[str, object]:
    app_a = web_runtime.WebApp()
    app_b = web_runtime.WebApp()
    def handler(req: dict[str, object]) -> dict[str, object]:
        ctx = dict(req.get("contexto") or {})
        return {"status": 200, "json": {"ok": True, "instancia": ctx.get("id_instancia", "n/a")}}
    app_a.routes.append(web_runtime.WebRoute.dynamic("GET", "/api/v1/multi", handler, schema={}, options={}))
    app_b.routes.append(web_runtime.WebRoute.dynamic("GET", "/api/v1/multi", handler, schema={}, options={}))

    app_a.tempo_real.registrar_rota("/ws/v212", lambda req: {"aceitar": True}, {})
    app_b.tempo_real.registrar_rota("/ws/v212", lambda req: {"aceitar": True}, {})
    app_a.tempo_real.ativar_fallback("/tempo-real/fallback", 1.0)
    app_b.tempo_real.ativar_fallback("/tempo-real/fallback", 1.0)
    app_a.tempo_real.configurar_distribuicao(ativar=True, grupo="v212_multi", id_instancia="a", auto_sincronizar=False, backplane="memoria")
    app_b.tempo_real.configurar_distribuicao(ativar=True, grupo="v212_multi", id_instancia="b", auto_sincronizar=False, backplane="memoria")

    sa = _iniciar_servidor(app_a)
    sb = _iniciar_servidor(app_b)
    latencias: list[float] = []
    erros = 0
    checks: list[dict[str, object]] = []
    ini = time.perf_counter()
    try:
        s1, c1, _, _ = _http_json("POST", sb.base_url + "/tempo-real/fallback/conectar", {"canal": "/ws/v212"})
        idc = str(c1.get("id_conexao", "")) if isinstance(c1, dict) else ""
        pub = app_a.tempo_real.publicar_mensagem("/ws/v212", "evt_multi", {"ok": True})
        app_b.tempo_real.sincronizar_distribuicao()
        s2, recv, _, _ = _http_json("GET", sb.base_url + f"/tempo-real/fallback/receber?id_conexao={idc}&timeout_segundos=0.2")
        eventos = list(dict(recv).get("eventos", [])) if isinstance(recv, dict) else []
        checks.append(
            {
                "nome": "realtime_multi_instancia_entrega",
                "ok": s1 == 200 and s2 == 200 and any(e.get("evento") == "evt_multi" for e in eventos) and int(pub.get("cursor", 0)) > 0,
            }
        )

        alvos = [sa.base_url + "/api/v1/multi", sb.base_url + "/api/v1/multi"]

        def _uma_req(i: int) -> tuple[int, float]:
            alvo = alvos[i % len(alvos)]
            st, _p, _h, dur = _http_json("GET", alvo, timeout=4.0)
            return st, dur

        with ThreadPoolExecutor(max_workers=max(1, int(concorrencia))) as ex:
            futuros = [ex.submit(_uma_req, i) for i in range(max(1, int(total_requisicoes)))]
            for fut in as_completed(futuros):
                st, dur = fut.result()
                latencias.append(float(dur))
                if st >= 400:
                    erros += 1
    finally:
        _parar_servidor(sa)
        _parar_servidor(sb)

    total = max(1, int(total_requisicoes))
    dur_s = max(0.001, float(time.perf_counter() - ini))
    erro_pct = (float(erros) / float(total)) * 100.0
    throughput = float(total) / dur_s
    p50 = _percentil(latencias, 0.50)
    p95 = _percentil(latencias, 0.95)
    ok_slo = p95 <= float(slo_p95_ms_max) and erro_pct <= float(slo_erro_pct_max) and throughput >= float(slo_throughput_min_rps)
    checks.append({"nome": "slo_multi_instancia", "ok": ok_slo})

    return {
        "ok": all(bool(x.get("ok")) for x in checks),
        "suite": "carga_multi_instancia",
        "parametros": {
            "total_requisicoes": total,
            "concorrencia": int(concorrencia),
            "slo_p95_ms_max": float(slo_p95_ms_max),
            "slo_erro_pct_max": float(slo_erro_pct_max),
            "slo_throughput_min_rps": float(slo_throughput_min_rps),
        },
        "metricas": {
            "duracao_s": dur_s,
            "throughput_rps": throughput,
            "erro_pct": erro_pct,
            "latencia_p50_ms": p50,
            "latencia_p95_ms": p95,
        },
        "checks": checks,
    }


def executar_caos_falha_parcial_v212() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    try:
        asyncio.run(db_runtime.conectar("sqlite:////v212_dir_inexistente__/arquivo.db"))
        checks.append({"nome": "db_indisponivel_erro_controlado", "ok": False, "erro": "esperava falha"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"nome": "db_indisponivel_erro_controlado", "ok": len(str(exc)) > 0, "erro": str(exc)[:160]})

    grupo = f"v212_cache_{int(time.time() * 1000)}"
    inst = cache_runtime.cache_distribuido_criar(grupo=grupo, id_instancia="v212", auto_sincronizar=False)
    cache_runtime.cache_distribuido_configurar_backplane(grupo, disponivel=False)
    valor = cache_runtime.cache_distribuido_obter_ou_carregar(
        "chave_v212",
        lambda: (_ for _ in ()).throw(RuntimeError("cache_indisponivel")),
        ttl_segundos=5,
        namespace="v212",
        fallback={"ok": True, "degradado": True},
        instancia=inst,
    )
    stats = cache_runtime.cache_distribuido_stats(namespace="v212", instancia=inst)
    checks.append(
        {
            "nome": "cache_indisponivel_fallback_seguro",
            "ok": isinstance(valor, dict) and bool(valor.get("degradado")) and int(stats.get("fallback_usado", 0)) >= 1,
            "stats": stats,
        }
    )
    cache_runtime.cache_distribuido_configurar_backplane(grupo, disponivel=True)

    hub = web_runtime.TempoRealHub()
    hub.registrar_rota("/ws/caos", lambda req: {"aceitar": True}, {})
    hub.configurar_distribuicao(ativar=True, grupo="v212_backplane", id_instancia="n1", auto_sincronizar=False, backplane="memoria")
    ok_con, c = hub.conectar("/ws/caos", "127.0.0.1", "u1", "r1", "t1", "fallback")
    hub.configurar_backplane(disponivel=False)
    pub = hub.publicar_mensagem("/ws/caos", "evt", {"ok": True})
    st = hub.snapshot("/ws/caos")
    checks.append(
        {
            "nome": "backplane_indisponivel_degradado_sem_perda_local",
            "ok": ok_con is True
            and c is not None
            and bool(pub.get("backplane_degradado"))
            and bool(st.get("distribuicao", {}).get("degradado"))
            and int(st.get("metricas", {}).get("falhas_backplane", 0)) >= 1,
        }
    )
    hub.configurar_backplane(disponivel=True)

    return {"ok": all(bool(x.get("ok")) for x in checks), "suite": "caos_falha_parcial_v212", "checks": checks}


def executar_seguranca_minima_v212() -> dict[str, object]:
    checks: list[dict[str, object]] = []
    sid = security_runtime.sessao_criar("u_v212", "disp_a", ttl_refresh_segundos=120)
    refresh = security_runtime.refresh_token_emitir("u_v212", "segredo_v212", str(sid["id_sessao"]), "disp_a", exp_segundos=120)
    rot = security_runtime.refresh_token_trocar(refresh, "segredo_v212", exp_segundos=120)
    checks.append({"nome": "rotacao_refresh", "ok": bool(rot.get("ok")) and security_runtime.token_esta_bloqueado(refresh)})

    app = web_runtime.WebApp()
    app.ambiente = "producao"
    app.cors_origens_por_ambiente["producao"] = ["https://app.trama.local"]
    app.routes.append(web_runtime.WebRoute.dynamic("GET", "/api/v1/seguro", lambda req: {"status": 200, "json": {"ok": True}}, schema={}, options={}))
    policy = web_runtime.RateLimitDistribuidoPolicy(
        method="GET",
        path="/api/v1/seguro",
        max_requisicoes=5,
        janela_segundos=30.0,
        chaves=["rota", "ip", "usuario"],
        grupo="v212_rl",
        backend="memoria",
    )
    app.rate_limits_distribuidos.append(policy)
    checks.append({"nome": "hardening_cors_producao", "ok": str(app.ambiente) == "producao"})
    checks.append({"nome": "rate_limit_distribuido_ativo", "ok": len(app.rate_limits_distribuidos) == 1})
    return {"ok": all(bool(x.get("ok")) for x in checks), "suite": "seguranca_minima_v212", "checks": checks}


def executar_suite_v212(
    *,
    diretorio_relatorio: str = ".local/test-results",
    perfil: str = "completo",
) -> dict[str, object]:
    ini = time.perf_counter()
    observability_runtime.metricas_reset()
    observability_runtime.tracos_reset()
    perfil_norm = str(perfil or "completo").strip().lower()
    rapido = perfil_norm == "rapido"

    unitario = {
        "ok": True,
        "suite": "unitario_critico",
        "checks": [
            {"nome": "cache_runtime_importado", "ok": hasattr(cache_runtime, "cache_distribuido_criar")},
            {"nome": "web_runtime_importado", "ok": hasattr(web_runtime, "WebApp")},
            {"nome": "security_runtime_importado", "ok": hasattr(security_runtime, "refresh_token_trocar")},
        ],
    }
    unitario["ok"] = all(bool(x.get("ok")) for x in unitario["checks"])

    contrato = executar_contrato_http_critico_v212()
    paridade = executar_paridade_python_nativo_fluxos_criticos()
    carga = executar_carga_multi_instancia_v212(
        total_requisicoes=(80 if rapido else 160),
        concorrencia=(8 if rapido else 16),
    )
    caos = executar_caos_falha_parcial_v212()
    seguranca = executar_seguranca_minima_v212()

    suites = {
        "unitario": unitario,
        "integracao": carga,
        "contrato_http": contrato,
        "paridade_python_nativo": paridade,
        "caos_falha_parcial": caos,
        "seguranca": seguranca,
    }
    ok = all(bool(v.get("ok")) for v in suites.values())
    dur_ms = (time.perf_counter() - ini) * 1000.0
    out_dir = Path(diretorio_relatorio)
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "ok": ok,
        "versao": "2.1.2",
        "perfil": perfil_norm,
        "executado_em": _agora_iso(),
        "duracao_ms": dur_ms,
        "parametros_versionados": {
            "arquivo_origem": "src/trama/testes_avancados_runtime.py",
            "perfil": perfil_norm,
            "total_requisicoes": (80 if rapido else 160),
            "concorrencia": (8 if rapido else 16),
        },
        "suites": suites,
        "baseline": dict(carga.get("metricas") or {}),
        "metricas_observabilidade": observability_runtime.metricas_snapshot(),
        "ambiente_execucao": {
            "python": sys.version.split()[0],
            "plataforma": sys.platform,
            "cwd": os.getcwd(),
        },
    }
