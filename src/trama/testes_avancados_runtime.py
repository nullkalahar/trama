"""Harness oficial de testes avancados da Trama (v2.0.8)."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import time
from typing import Any
from urllib import error, parse, request

from . import cache_runtime
from . import db_runtime
from . import observability_runtime
from . import security_runtime
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
    linhas.append("# Relatorio v2.0.8 - Testes Avancados")
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
