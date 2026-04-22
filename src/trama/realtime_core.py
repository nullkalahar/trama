"""Core de tempo real da Trama."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import socket
import threading
import time
from typing import Protocol
import uuid

from . import observability_runtime


@dataclass
class _TempoRealEventoDistribuido:
    seq: int
    tipo: str
    dados: dict[str, object]
    instancia_origem: str
    at: float = field(default_factory=time.time)


class BackplaneTempoReal(Protocol):
    def set_disponivel(self, disponivel: bool) -> None:
        ...

    def publicar_evento(self, tipo: str, dados: dict[str, object], instancia_origem: str) -> int:
        ...

    def coletar_eventos(self, desde_seq: int) -> list[_TempoRealEventoDistribuido]:
        ...


class _TempoRealBackplaneMemoria:
    def __init__(self, grupo: str) -> None:
        self.grupo = grupo
        self._lock = threading.RLock()
        self._seq = 0
        self._eventos: list[_TempoRealEventoDistribuido] = []
        self._disponivel = True

    def set_disponivel(self, disponivel: bool) -> None:
        with self._lock:
            self._disponivel = bool(disponivel)

    def _check(self) -> None:
        if not self._disponivel:
            raise RuntimeError(f"Backplane tempo real indisponivel para grupo '{self.grupo}'.")

    def publicar_evento(self, tipo: str, dados: dict[str, object], instancia_origem: str) -> int:
        with self._lock:
            self._check()
            self._seq += 1
            self._eventos.append(
                _TempoRealEventoDistribuido(
                    seq=self._seq,
                    tipo=str(tipo),
                    dados=dict(dados or {}),
                    instancia_origem=str(instancia_origem),
                )
            )
            if len(self._eventos) > 20000:
                del self._eventos[: len(self._eventos) - 20000]
            return self._seq

    def coletar_eventos(self, desde_seq: int) -> list[_TempoRealEventoDistribuido]:
        with self._lock:
            self._check()
            return [e for e in self._eventos if e.seq > int(desde_seq)]


class _TempoRealBackplaneRedis:
    def __init__(self, grupo: str, url: str, chave_prefixo: str = "trama:tempo_real") -> None:
        self.grupo = str(grupo or "padrao")
        self.url = str(url)
        self._prefixo = f"{str(chave_prefixo).strip(':')}:{self.grupo}"
        self._disponivel = True
        try:
            redis_mod = __import__("redis")
            self._cliente = redis_mod.Redis.from_url(self.url, decode_responses=True)
            self._cliente.ping()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Falha ao inicializar backplane redis: {exc}") from exc

    def set_disponivel(self, disponivel: bool) -> None:
        self._disponivel = bool(disponivel)

    def _check(self) -> None:
        if not self._disponivel:
            raise RuntimeError(f"Backplane redis indisponivel para grupo '{self.grupo}'.")

    def _k_seq(self) -> str:
        return f"{self._prefixo}:seq"

    def _k_log(self) -> str:
        return f"{self._prefixo}:eventos"

    def publicar_evento(self, tipo: str, dados: dict[str, object], instancia_origem: str) -> int:
        self._check()
        seq = int(self._cliente.incr(self._k_seq()))
        payload = json.dumps(
            {
                "seq": seq,
                "tipo": str(tipo),
                "dados": dict(dados or {}),
                "instancia_origem": str(instancia_origem),
                "at": time.time(),
            },
            ensure_ascii=False,
        )
        pipe = self._cliente.pipeline()
        pipe.rpush(self._k_log(), payload)
        pipe.ltrim(self._k_log(), -20000, -1)
        pipe.execute()
        return seq

    def coletar_eventos(self, desde_seq: int) -> list[_TempoRealEventoDistribuido]:
        self._check()
        itens = self._cliente.lrange(self._k_log(), 0, -1)
        out: list[_TempoRealEventoDistribuido] = []
        for raw in itens:
            try:
                obj = json.loads(str(raw))
            except json.JSONDecodeError:
                continue
            seq = int(obj.get("seq", 0))
            if seq <= int(desde_seq):
                continue
            out.append(
                _TempoRealEventoDistribuido(
                    seq=seq,
                    tipo=str(obj.get("tipo", "")),
                    dados=dict(obj.get("dados", {})),
                    instancia_origem=str(obj.get("instancia_origem", "")),
                    at=float(obj.get("at", time.time())),
                )
            )
        return out


_TR_BACKPLANES_LOCK = threading.RLock()
_TR_BACKPLANES_MEM: dict[str, _TempoRealBackplaneMemoria] = {}


def _tempo_real_backplane_memoria(grupo: str) -> _TempoRealBackplaneMemoria:
    g = str(grupo or "padrao").strip() or "padrao"
    with _TR_BACKPLANES_LOCK:
        if g not in _TR_BACKPLANES_MEM:
            _TR_BACKPLANES_MEM[g] = _TempoRealBackplaneMemoria(g)
        return _TR_BACKPLANES_MEM[g]


def criar_backplane_tempo_real(
    *,
    tipo: str,
    grupo: str,
    redis_url: str | None = None,
    chave_prefixo_redis: str = "trama:tempo_real",
) -> BackplaneTempoReal:
    tipo_norm = str(tipo or "memoria").lower()
    if tipo_norm in {"memoria", "memory"}:
        return _tempo_real_backplane_memoria(grupo)
    if tipo_norm == "redis":
        if not redis_url:
            raise ValueError("web_tempo_real_configurar_distribuicao exige 'redis_url' para backplane redis.")
        return _TempoRealBackplaneRedis(grupo, redis_url, chave_prefixo=chave_prefixo_redis)
    raise ValueError("backplane de tempo real inválido; use 'memoria' ou 'redis'.")


@dataclass
class TempoRealConexao:
    id_conexao: str
    canal: str
    ip: str
    id_usuario: str | None
    id_requisicao: str
    id_traco: str
    modo: str  # websocket | fallback
    socket_conn: socket.socket | None = None
    ativa: bool = True
    criada_em: float = field(default_factory=time.time)
    ultimo_heartbeat_em: float = field(default_factory=time.time)
    salas: set[str] = field(default_factory=set)
    fila_eventos: list[dict[str, object]] = field(default_factory=list)
    janela_mensagens: list[float] = field(default_factory=list)
    cursor_ultimo_confirmado: int = 0

    def enfileirar(self, payload: dict[str, object], limite_fila: int = 1000) -> None:
        item = dict(payload)
        cur_raw = item.get("cursor")
        cur_val = int(cur_raw) if isinstance(cur_raw, (int, float)) else 0
        if cur_val > 0 and self.fila_eventos:
            idx = len(self.fila_eventos)
            for i, existente in enumerate(self.fila_eventos):
                e_cur_raw = existente.get("cursor")
                if not isinstance(e_cur_raw, (int, float)):
                    continue
                if int(e_cur_raw) > cur_val:
                    idx = i
                    break
            self.fila_eventos.insert(idx, item)
        else:
            self.fila_eventos.append(item)
        if len(self.fila_eventos) > limite_fila:
            del self.fila_eventos[0 : len(self.fila_eventos) - limite_fila]

    def drenar(self, limite: int = 100) -> list[dict[str, object]]:
        if limite <= 0:
            return []
        out = self.fila_eventos[:limite]
        del self.fila_eventos[:limite]
        return out


class TempoRealHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.rotas: dict[str, dict[str, object]] = {}
        self.conexoes: dict[str, dict[str, TempoRealConexao]] = {}
        self.salas: dict[str, dict[str, set[str]]] = {}
        self.presenca_remota: dict[str, dict[str, dict[str, object]]] = {}
        self.salas_remotas: dict[str, dict[str, set[str]]] = {}
        self.fallback_ativo = False
        self.fallback_prefixo = "/tempo-real/fallback"
        self.fallback_timeout_segundos = 20.0
        self.limites: dict[str, float] = {
            "max_conexoes_total": 2000,
            "max_conexoes_por_ip": 200,
            "max_conexoes_por_usuario": 100,
            "max_conexoes_por_sala": 500,
            "max_payload_bytes": 64 * 1024,
            "max_mensagens_por_janela": 120,
            "max_mensagens_por_janela_usuario": 240,
            "max_mensagens_por_janela_sala": 500,
            "janela_rate_segundos": 60.0,
            "heartbeat_segundos": 30.0,
            "janela_replay_segundos": 300.0,
            "max_eventos_historico_canal": 2000,
        }
        self.ordenacao_canal: dict[str, int] = {}
        self.pendencias_ack: dict[str, dict[str, dict[str, object]]] = {}
        self.historico_canal: dict[str, list[dict[str, object]]] = {}
        self.janela_mensagens_usuario: dict[str, list[float]] = {}
        self.janela_mensagens_sala: dict[str, list[float]] = {}
        self.metricas: dict[str, float] = {
            "entregues": 0.0,
            "acks": 0.0,
            "nacks": 0.0,
            "retries": 0.0,
            "reenvios": 0.0,
            "reconexoes": 0.0,
            "desconexoes": 0.0,
            "falhas_backplane": 0.0,
            "degradacao_eventos": 0.0,
            "latencia_entrega_ms_total": 0.0,
            "latencia_entrega_ms_amostras": 0.0,
            "latencia_reconexao_ms_total": 0.0,
            "latencia_reconexao_ms_amostras": 0.0,
            "sincronizacoes": 0.0,
            "eventos_remotos_aplicados": 0.0,
        }
        self.distribuicao_ativa = False
        self.grupo_distribuicao = "padrao"
        self.id_instancia = f"tr_{uuid.uuid4().hex[:8]}"
        self.auto_sincronizar_distribuicao = True
        self.backplane_tipo = "memoria"
        self._backplane: BackplaneTempoReal | None = None
        self._seq_distribuido_aplicado = 0
        self._backplane_degradado = False

    def registrar_rota(self, caminho: str, handler: object, opcoes: dict[str, object] | None = None) -> None:
        path = caminho if caminho.startswith("/") else f"/{caminho}"
        with self._lock:
            self.rotas[path] = {"handler": handler, "opcoes": dict(opcoes or {})}
            self.conexoes.setdefault(path, {})
            self.salas.setdefault(path, {})
            self.presenca_remota.setdefault(path, {})
            self.salas_remotas.setdefault(path, {})
            self.historico_canal.setdefault(path, [])

    def definir_limites(self, limites: dict[str, object]) -> None:
        with self._lock:
            for k, v in dict(limites or {}).items():
                if k in self.limites:
                    self.limites[k] = float(v)  # type: ignore[assignment]

    def configurar_distribuicao(
        self,
        *,
        ativar: bool = True,
        grupo: str = "padrao",
        id_instancia: str | None = None,
        auto_sincronizar: bool = True,
        backplane: str = "memoria",
        redis_url: str | None = None,
        chave_prefixo_redis: str = "trama:tempo_real",
    ) -> dict[str, object]:
        with self._lock:
            self.distribuicao_ativa = bool(ativar)
            self.grupo_distribuicao = str(grupo or "padrao").strip() or "padrao"
            self.id_instancia = str(id_instancia or self.id_instancia).strip() or self.id_instancia
            self.auto_sincronizar_distribuicao = bool(auto_sincronizar)
            self.backplane_tipo = str(backplane or "memoria").lower()
            self._seq_distribuido_aplicado = 0
            self._backplane_degradado = False
            if not self.distribuicao_ativa:
                self._backplane = None
                return {"ok": True, "ativo": False, "grupo": self.grupo_distribuicao, "instancia": self.id_instancia}

            self._backplane = criar_backplane_tempo_real(
                tipo=self.backplane_tipo,
                grupo=self.grupo_distribuicao,
                redis_url=redis_url,
                chave_prefixo_redis=chave_prefixo_redis,
            )

            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "distribuicao_configurada",
                labels={
                    "grupo": self.grupo_distribuicao,
                    "instancia": self.id_instancia,
                    "backplane": self.backplane_tipo,
                    "auto_sync": str(self.auto_sincronizar_distribuicao).lower(),
                },
            )
            return {
                "ok": True,
                "ativo": True,
                "grupo": self.grupo_distribuicao,
                "instancia": self.id_instancia,
                "backplane": self.backplane_tipo,
                "auto_sincronizar": self.auto_sincronizar_distribuicao,
            }

    def configurar_backplane(self, disponivel: bool = True) -> dict[str, object]:
        with self._lock:
            bp = self._backplane
            if bp is None:
                return {"ok": False, "codigo": "DISTRIBUICAO_NAO_CONFIGURADA"}
            if hasattr(bp, "set_disponivel"):
                bp.set_disponivel(bool(disponivel))
            self._backplane_degradado = not bool(disponivel)
            return {"ok": True, "disponivel": bool(disponivel)}

    def _metrica_inc(self, chave: str, valor: float = 1.0) -> None:
        self.metricas[chave] = float(self.metricas.get(chave, 0.0) + float(valor))

    def _publicar_backplane(self, tipo: str, dados: dict[str, object]) -> int | None:
        if not self.distribuicao_ativa or self._backplane is None:
            return None
        try:
            seq = self._backplane.publicar_evento(tipo, dict(dados or {}), self.id_instancia)
            self._backplane_degradado = False
            return int(seq)
        except Exception as exc:  # noqa: BLE001
            self._metrica_inc("falhas_backplane", 1.0)
            self._metrica_inc("degradacao_eventos", 1.0)
            self._backplane_degradado = True
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "backplane_falha",
                labels={"instancia": self.id_instancia, "erro": str(exc)[:120]},
            )
            return None

    def sincronizar_distribuicao(self) -> int:
        if not self.distribuicao_ativa or self._backplane is None:
            return 0
        start = time.perf_counter()
        try:
            eventos = self._backplane.coletar_eventos(self._seq_distribuido_aplicado)
        except Exception as exc:  # noqa: BLE001
            self._metrica_inc("falhas_backplane", 1.0)
            self._backplane_degradado = True
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "backplane_falha",
                labels={"instancia": self.id_instancia, "erro": str(exc)[:120]},
            )
            return 0

        aplicados = 0
        with self._lock:
            for ev in eventos:
                self._seq_distribuido_aplicado = max(self._seq_distribuido_aplicado, int(ev.seq))
                if str(ev.instancia_origem) == self.id_instancia:
                    continue
                self._aplicar_evento_distribuido_locked(ev)
                aplicados += 1
            if aplicados > 0:
                self._metrica_inc("eventos_remotos_aplicados", float(aplicados))
            self._metrica_inc("sincronizacoes", 1.0)
        observability_runtime.metrica_observar(
            "tempo_real.latencia_sincronizacao_ms",
            (time.perf_counter() - start) * 1000.0,
            {"instancia": self.id_instancia, "grupo": self.grupo_distribuicao},
        )
        return aplicados

    def _sync_if_needed(self) -> None:
        if self.distribuicao_ativa and self.auto_sincronizar_distribuicao:
            self.sincronizar_distribuicao()

    def ativar_fallback(self, prefixo: str = "/tempo-real/fallback", timeout_segundos: float = 20.0) -> None:
        with self._lock:
            self.fallback_ativo = True
            self.fallback_prefixo = prefixo if str(prefixo).startswith("/") else f"/{prefixo}"
            self.fallback_timeout_segundos = max(1.0, float(timeout_segundos))

    def snapshot(self, canal: str | None = None) -> dict[str, object]:
        self._sync_if_needed()
        with self._lock:
            canais = [canal] if canal else sorted(self.rotas.keys())
            out_canais: list[dict[str, object]] = []
            total = 0
            total_remoto = 0
            for c in canais:
                conns = self.conexoes.get(c, {})
                salas = self.salas.get(c, {})
                conns_remotas = self.presenca_remota.get(c, {})
                salas_remotas = self.salas_remotas.get(c, {})
                total += len(conns)
                total_remoto += len(conns_remotas)
                backlog_local = sum(len(cx.fila_eventos) for cx in conns.values())
                backlog_sala = {
                    s: sum(len(conns[x].fila_eventos) for x in ids if x in conns)
                    for s, ids in salas.items()
                }
                out_canais.append(
                    {
                        "canal": c,
                        "conexoes_ativas": len(conns),
                        "conexoes_remotas": len(conns_remotas),
                        "salas": {s: len(ids) for s, ids in salas.items()},
                        "salas_remotas": {s: len(ids) for s, ids in salas_remotas.items()},
                        "pendencias_ack": len(self.pendencias_ack.get(c, {})),
                        "backlog_local": backlog_local,
                        "backlog_por_sala": backlog_sala,
                    }
                )
            lat_ent_am = float(self.metricas.get("latencia_entrega_ms_amostras", 0.0))
            lat_ent_tot = float(self.metricas.get("latencia_entrega_ms_total", 0.0))
            lat_rec_am = float(self.metricas.get("latencia_reconexao_ms_amostras", 0.0))
            lat_rec_tot = float(self.metricas.get("latencia_reconexao_ms_total", 0.0))
            return {
                "ok": True,
                "total_conexoes_ativas": total,
                "total_conexoes_remotas": total_remoto,
                "canais": out_canais,
                "fallback_ativo": self.fallback_ativo,
                "fallback_prefixo": self.fallback_prefixo,
                "limites": dict(self.limites),
                "distribuicao": {
                    "ativo": self.distribuicao_ativa,
                    "grupo": self.grupo_distribuicao,
                    "instancia": self.id_instancia,
                    "backplane": self.backplane_tipo,
                    "seq_sincronizado": self._seq_distribuido_aplicado,
                    "degradado": self._backplane_degradado,
                },
                "metricas": {
                    "entregues": int(self.metricas.get("entregues", 0.0)),
                    "ack": int(self.metricas.get("acks", 0.0)),
                    "nack": int(self.metricas.get("nacks", 0.0)),
                    "retries": int(self.metricas.get("retries", 0.0)),
                    "reenvios": int(self.metricas.get("reenvios", 0.0)),
                    "reconexoes": int(self.metricas.get("reconexoes", 0.0)),
                    "desconexoes": int(self.metricas.get("desconexoes", 0.0)),
                    "falhas_backplane": int(self.metricas.get("falhas_backplane", 0.0)),
                    "degradacao_eventos": int(self.metricas.get("degradacao_eventos", 0.0)),
                    "eventos_remotos_aplicados": int(self.metricas.get("eventos_remotos_aplicados", 0.0)),
                    "latencia_entrega_media_ms": (lat_ent_tot / lat_ent_am) if lat_ent_am > 0 else 0.0,
                    "latencia_reconexao_media_ms": (lat_rec_tot / lat_rec_am) if lat_rec_am > 0 else 0.0,
                },
            }

    def _contagem_total(self) -> int:
        return sum(len(v) for v in self.conexoes.values())

    def _contagem_ip(self, ip: str) -> int:
        total = 0
        for conns in self.conexoes.values():
            for c in conns.values():
                if c.ip == ip:
                    total += 1
        return total

    def _contagem_usuario(self, id_usuario: str) -> int:
        total = 0
        for conns in self.conexoes.values():
            for c in conns.values():
                if c.id_usuario == id_usuario:
                    total += 1
        return total

    def conectar(
        self,
        canal: str,
        ip: str,
        id_usuario: str | None,
        id_requisicao: str,
        id_traco: str,
        modo: str,
        socket_conn: socket.socket | None = None,
        cursor_ultimo: int | None = None,
    ) -> tuple[bool, dict[str, object] | TempoRealConexao]:
        self._sync_if_needed()
        with self._lock:
            if canal not in self.rotas:
                return False, {"codigo": "CANAL_NAO_ENCONTRADO", "mensagem": "Canal de tempo real não encontrado."}
            if self._contagem_total() >= int(self.limites["max_conexoes_total"]):
                return False, {"codigo": "LIMITE_CONEXOES_TOTAL", "mensagem": "Limite global de conexões atingido."}
            if self._contagem_ip(ip) >= int(self.limites["max_conexoes_por_ip"]):
                return False, {"codigo": "LIMITE_CONEXOES_IP", "mensagem": "Limite de conexões por IP atingido."}
            if id_usuario and self._contagem_usuario(id_usuario) >= int(self.limites["max_conexoes_por_usuario"]):
                return False, {"codigo": "LIMITE_CONEXOES_USUARIO", "mensagem": "Limite de conexões por usuário atingido."}

            c = TempoRealConexao(
                id_conexao=uuid.uuid4().hex,
                canal=canal,
                ip=ip,
                id_usuario=id_usuario,
                id_requisicao=id_requisicao,
                id_traco=id_traco,
                modo=modo,
                socket_conn=socket_conn,
            )
            self.conexoes.setdefault(canal, {})[c.id_conexao] = c
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "conexao_aberta",
                labels={"canal": canal, "modo": modo, "id_usuario": id_usuario or "anonimo"},
            )
            if cursor_ultimo is not None and int(cursor_ultimo) > 0:
                ini = time.perf_counter()
                replay = self._replay_desde_cursor_locked(c, int(cursor_ultimo))
                self._metrica_inc("reconexoes", 1.0)
                self.metricas["latencia_reconexao_ms_total"] += (time.perf_counter() - ini) * 1000.0
                self.metricas["latencia_reconexao_ms_amostras"] += 1.0
                observability_runtime.registrar_runtime_metrica(
                    "tempo_real",
                    "reconexao_replay",
                    valor=float(replay),
                    labels={"canal": canal, "instancia": self.id_instancia},
                )
            self._emitir_presenca_locked(canal, c, online=True)
            self._publicar_backplane(
                "presenca",
                {
                    "acao": "conectar",
                    "canal": canal,
                    "id_conexao": c.id_conexao,
                    "id_usuario": c.id_usuario,
                    "ip": c.ip,
                    "modo": c.modo,
                    "cursor_ultimo": int(cursor_ultimo or 0),
                },
            )
            return True, c

    def desconectar(self, conexao: TempoRealConexao, motivo: str = "encerrado") -> None:
        self._sync_if_needed()
        with self._lock:
            conns = self.conexoes.get(conexao.canal, {})
            if conexao.id_conexao in conns:
                del conns[conexao.id_conexao]
            for ids in self.salas.get(conexao.canal, {}).values():
                ids.discard(conexao.id_conexao)
            conexao.ativa = False
            self._metrica_inc("desconexoes", 1.0)
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "conexao_fechada",
                labels={"canal": conexao.canal, "motivo": motivo},
            )
            self._emitir_presenca_locked(conexao.canal, conexao, online=False)
            self._publicar_backplane(
                "presenca",
                {
                    "acao": "desconectar",
                    "canal": conexao.canal,
                    "id_conexao": conexao.id_conexao,
                    "id_usuario": conexao.id_usuario,
                },
            )

    def entrar_sala(self, conexao: TempoRealConexao, sala: str) -> tuple[bool, dict[str, object] | None]:
        self._sync_if_needed()
        with self._lock:
            sala_norm = str(sala)
            ids = self.salas.setdefault(conexao.canal, {}).setdefault(sala_norm, set())
            if len(ids) >= int(self.limites["max_conexoes_por_sala"]):
                return False, {"codigo": "LIMITE_CONEXOES_SALA", "mensagem": "Limite de conexões da sala excedido."}
            ids.add(conexao.id_conexao)
            conexao.salas.add(sala_norm)
            self._publicar_backplane(
                "sala",
                {"acao": "entrar", "canal": conexao.canal, "id_conexao": conexao.id_conexao, "sala": sala_norm},
            )
            return True, None

    def sair_sala(self, conexao: TempoRealConexao, sala: str) -> None:
        self._sync_if_needed()
        with self._lock:
            sala_norm = str(sala)
            ids = self.salas.setdefault(conexao.canal, {}).setdefault(sala_norm, set())
            ids.discard(conexao.id_conexao)
            conexao.salas.discard(sala_norm)
            self._publicar_backplane(
                "sala",
                {"acao": "sair", "canal": conexao.canal, "id_conexao": conexao.id_conexao, "sala": sala_norm},
            )

    def _selecionar_destinos_locked(
        self,
        canal: str,
        id_conexao: str | None = None,
        id_usuario: str | None = None,
        sala: str | None = None,
    ) -> list[TempoRealConexao]:
        conns = list(self.conexoes.get(canal, {}).values())
        if id_conexao:
            return [c for c in conns if c.id_conexao == id_conexao]
        if id_usuario:
            return [c for c in conns if c.id_usuario == id_usuario]
        if sala:
            ids = self.salas.get(canal, {}).get(sala, set())
            return [c for c in conns if c.id_conexao in ids]
        return conns

    def emitir(
        self,
        canal: str,
        evento: str,
        dados: object | None = None,
        *,
        sala: str | None = None,
        id_usuario: str | None = None,
        id_conexao: str | None = None,
        origem: TempoRealConexao | None = None,
    ) -> int:
        self._sync_if_needed()
        with self._lock:
            destinos = self._selecionar_destinos_locked(canal, id_conexao=id_conexao, id_usuario=id_usuario, sala=sala)
            payload = {
                "ok": True,
                "evento": str(evento),
                "dados": dados if dados is not None else {},
                "canal": canal,
                "sala": sala,
                "cursor": int(self.ordenacao_canal.get(canal, 0)),
                "id_usuario_origem": origem.id_usuario if origem else None,
                "id_conexao_origem": origem.id_conexao if origem else None,
                "ts": time.time(),
            }
            for d in destinos:
                d.enfileirar(payload)
            self._metrica_inc("entregues", float(len(destinos)))
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "broadcast",
                valor=len(destinos),
                labels={"canal": canal, "evento": evento},
            )
            return len(destinos)

    def publicar_mensagem(
        self,
        canal: str,
        evento: str,
        dados: object | None = None,
        *,
        sala: str | None = None,
        id_usuario: str | None = None,
        id_conexao: str | None = None,
        exigir_ack: bool = False,
        origem: TempoRealConexao | None = None,
    ) -> dict[str, object]:
        self._sync_if_needed()
        with self._lock:
            id_mensagem = uuid.uuid4().hex
            ts = time.time()
            seq_local = int(self.ordenacao_canal.get(canal, 0) + 1)
            self.ordenacao_canal[canal] = seq_local
            dados_evento = {
                "id_mensagem": id_mensagem,
                "evento": str(evento),
                "dados": dados if dados is not None else {},
                "canal": str(canal),
                "sala": sala,
                "id_usuario": id_usuario,
                "id_conexao": id_conexao,
                "exigir_ack": bool(exigir_ack),
                "id_usuario_origem": origem.id_usuario if origem else None,
                "id_conexao_origem": origem.id_conexao if origem else None,
                "ts": ts,
            }
            cursor = self._publicar_backplane("publicar_mensagem", dados_evento) or seq_local
            destinos = self._selecionar_destinos_locked(canal, id_conexao=id_conexao, id_usuario=id_usuario, sala=sala)
            envelope = {
                "ok": True,
                "evento": str(evento),
                "dados": dados if dados is not None else {},
                "canal": canal,
                "sala": sala,
                "id_mensagem": id_mensagem,
                "message_id": id_mensagem,
                "ordem": int(cursor),
                "seq": int(cursor),
                "cursor": int(cursor),
                "exigir_ack": bool(exigir_ack),
                "id_usuario_origem": origem.id_usuario if origem else None,
                "id_conexao_origem": origem.id_conexao if origem else None,
                "ts": ts,
            }
            ini_entrega = time.perf_counter()
            for d in destinos:
                d.enfileirar(envelope)
            self._registrar_historico_locked(canal, envelope)
            self.metricas["latencia_entrega_ms_total"] += (time.perf_counter() - ini_entrega) * 1000.0
            self.metricas["latencia_entrega_ms_amostras"] += 1.0
            self._metrica_inc("entregues", float(len(destinos)))
            if exigir_ack:
                pend = self.pendencias_ack.setdefault(canal, {})
                pend[id_mensagem] = {
                    "envelope": envelope,
                    "pendentes": {d.id_conexao for d in destinos},
                    "confirmados": set(),
                    "tentativas_reenvio": 0,
                    "criado_em": ts,
                }
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "mensagem_publicada",
                valor=len(destinos),
                labels={"canal": canal, "evento": evento, "ack": str(bool(exigir_ack)).lower()},
            )
            return {
                "id_mensagem": id_mensagem,
                "ordem": int(cursor),
                "cursor": int(cursor),
                "destinos": len(destinos),
                "ack": bool(exigir_ack),
                "backplane_degradado": bool(self._backplane_degradado),
            }

    def confirmar_ack(self, canal: str, id_mensagem: str, id_conexao: str, status: str = "ack") -> dict[str, object]:
        self._sync_if_needed()
        with self._lock:
            out = self._confirmar_ack_locked(canal, id_mensagem, id_conexao, status=status, propagar=True)
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "ack_recebido",
                labels={"canal": canal, "status": str(status)},
            )
            return out

    def reenviar_pendentes(self, canal: str, id_mensagem: str | None = None) -> dict[str, object]:
        self._sync_if_needed()
        with self._lock:
            reenvios = self._reenviar_pendentes_locked(canal, id_mensagem=id_mensagem, propagar=True)
            observability_runtime.registrar_runtime_metrica(
                "tempo_real",
                "reenvio_pendente",
                valor=reenvios,
                labels={"canal": canal},
            )
            return {"ok": True, "reenvios": reenvios}

    def receber_fallback(
        self,
        conexao: TempoRealConexao,
        timeout_segundos: float | None = None,
        limite: int = 50,
        cursor_desde: int | None = None,
    ) -> list[dict[str, object]]:
        self._sync_if_needed()
        if cursor_desde is not None and int(cursor_desde) > 0:
            with self._lock:
                self._replay_desde_cursor_locked(conexao, int(cursor_desde))
        limite_t = self.fallback_timeout_segundos if timeout_segundos is None else max(0.0, float(timeout_segundos))
        fim = time.time() + limite_t
        while time.time() <= fim:
            with self._lock:
                data = conexao.drenar(limite)
                if data:
                    for ev in data:
                        cur = int(ev.get("cursor", 0))
                        if cur > conexao.cursor_ultimo_confirmado:
                            conexao.cursor_ultimo_confirmado = cur
                if data:
                    return data
            time.sleep(0.05)
        return []

    def por_id(self, id_conexao: str) -> TempoRealConexao | None:
        with self._lock:
            for conns in self.conexoes.values():
                c = conns.get(id_conexao)
                if c is not None:
                    return c
        return None

    def rota_info(self, canal: str) -> dict[str, object] | None:
        self._sync_if_needed()
        with self._lock:
            return self.rotas.get(canal)

    def validar_rate(self, conexao: TempoRealConexao, mensagem: dict[str, object] | None = None) -> bool:
        now = time.time()
        janela = float(self.limites["janela_rate_segundos"])
        max_m = int(self.limites["max_mensagens_por_janela"])
        max_u = int(self.limites["max_mensagens_por_janela_usuario"])
        max_s = int(self.limites["max_mensagens_por_janela_sala"])
        with self._lock:
            conexao.janela_mensagens = [t for t in conexao.janela_mensagens if t >= now - janela]
            if len(conexao.janela_mensagens) >= max_m:
                return False
            conexao.janela_mensagens.append(now)
            if conexao.id_usuario:
                uid = str(conexao.id_usuario)
                bucket_u = [t for t in self.janela_mensagens_usuario.get(uid, []) if t >= now - janela]
                if len(bucket_u) >= max_u:
                    return False
                bucket_u.append(now)
                self.janela_mensagens_usuario[uid] = bucket_u
            if isinstance(mensagem, dict):
                sala = str(mensagem.get("sala") or "")
                if sala:
                    chave_sala = f"{conexao.canal}:{sala}"
                    bucket_s = [t for t in self.janela_mensagens_sala.get(chave_sala, []) if t >= now - janela]
                    if len(bucket_s) >= max_s:
                        return False
                    bucket_s.append(now)
                    self.janela_mensagens_sala[chave_sala] = bucket_s
        return True

    def _emitir_presenca_locked(self, canal: str, conexao: TempoRealConexao, online: bool) -> None:
        payload = {
            "id_usuario": conexao.id_usuario,
            "id_conexao": conexao.id_conexao,
            "online": bool(online),
            "canal": canal,
            "ts": time.time(),
        }
        for c in self.conexoes.get(canal, {}).values():
            c.enfileirar({"ok": True, "evento": "presenca", "dados": payload, "canal": canal, "ts": time.time()})

    def _registrar_historico_locked(self, canal: str, envelope: dict[str, object]) -> None:
        now = time.time()
        hist = self.historico_canal.setdefault(canal, [])
        hist.append(dict(envelope))
        ttl = float(self.limites.get("janela_replay_segundos", 300.0))
        min_ts = now - ttl
        hist[:] = [ev for ev in hist if float(ev.get("ts", now)) >= min_ts]
        limite = int(self.limites.get("max_eventos_historico_canal", 2000))
        if len(hist) > limite:
            del hist[: len(hist) - limite]

    def _replay_desde_cursor_locked(self, conexao: TempoRealConexao, cursor_ultimo: int) -> int:
        replay = 0
        for ev in self.historico_canal.get(conexao.canal, []):
            cur = int(ev.get("cursor", 0))
            if cur > int(cursor_ultimo):
                conexao.enfileirar(dict(ev))
                replay += 1
        return replay

    def _confirmar_ack_locked(
        self,
        canal: str,
        id_mensagem: str,
        id_conexao: str,
        *,
        status: str,
        propagar: bool,
    ) -> dict[str, object]:
        pend = self.pendencias_ack.get(canal, {})
        item = pend.get(str(id_mensagem))
        if item is None:
            return {"ok": False, "codigo": "MENSAGEM_NAO_ENCONTRADA"}
        pendentes = set(item.get("pendentes", set()))
        confirmados = set(item.get("confirmados", set()))
        s = str(status or "ack").lower()
        if s == "ack":
            if str(id_conexao) in pendentes:
                pendentes.remove(str(id_conexao))
            confirmados.add(str(id_conexao))
            self._metrica_inc("acks", 1.0)
        else:
            self._metrica_inc("nacks", 1.0)
            if str(id_conexao) not in pendentes:
                pendentes.add(str(id_conexao))
        item["pendentes"] = pendentes
        item["confirmados"] = confirmados
        item["ultimo_status"] = s
        if s != "ack":
            env = dict(item.get("envelope", {}))
            c = self.conexoes.get(canal, {}).get(str(id_conexao))
            if c is not None:
                c.enfileirar(env)
                self._metrica_inc("retries", 1.0)
        if not pendentes:
            del pend[str(id_mensagem)]
        if propagar:
            self._publicar_backplane(
                "ack",
                {
                    "canal": canal,
                    "id_mensagem": str(id_mensagem),
                    "id_conexao": str(id_conexao),
                    "status": s,
                },
            )
        return {"ok": True, "pendentes": len(pendentes), "confirmados": len(confirmados), "status": s}

    def _reenviar_pendentes_locked(self, canal: str, id_mensagem: str | None, *, propagar: bool) -> int:
        pend = self.pendencias_ack.get(canal, {})
        ids = [str(id_mensagem)] if id_mensagem else list(pend.keys())
        reenvios = 0
        for mid in ids:
            item = pend.get(mid)
            if item is None:
                continue
            env = dict(item.get("envelope", {}))
            alvos = sorted(str(x) for x in set(item.get("pendentes", set())))
            for cid in alvos:
                c = self.conexoes.get(canal, {}).get(cid)
                if c is not None:
                    c.enfileirar(env)
                    reenvios += 1
            item["tentativas_reenvio"] = int(item.get("tentativas_reenvio", 0)) + 1
        self._metrica_inc("reenvios", float(reenvios))
        if propagar:
            self._publicar_backplane(
                "reenviar",
                {"canal": canal, "id_mensagem": str(id_mensagem) if id_mensagem is not None else None},
            )
        return reenvios

    def _aplicar_evento_distribuido_locked(self, ev: _TempoRealEventoDistribuido) -> None:
        dados = dict(ev.dados or {})
        tipo = str(ev.tipo or "")
        canal = str(dados.get("canal") or "")
        if tipo == "presenca":
            acao = str(dados.get("acao") or "")
            rem = self.presenca_remota.setdefault(canal, {})
            id_c = str(dados.get("id_conexao") or "")
            if acao == "conectar":
                rem[id_c] = {
                    "id_conexao": id_c,
                    "id_usuario": dados.get("id_usuario"),
                    "ip": dados.get("ip"),
                    "modo": dados.get("modo"),
                }
            elif acao == "desconectar":
                rem.pop(id_c, None)
                for salas in self.salas_remotas.get(canal, {}).values():
                    salas.discard(id_c)
            return
        if tipo == "sala":
            acao = str(dados.get("acao") or "")
            sala = str(dados.get("sala") or "")
            id_c = str(dados.get("id_conexao") or "")
            ids = self.salas_remotas.setdefault(canal, {}).setdefault(sala, set())
            if acao == "entrar":
                ids.add(id_c)
            elif acao == "sair":
                ids.discard(id_c)
            return
        if tipo == "publicar_mensagem":
            id_mensagem = str(dados.get("id_mensagem") or uuid.uuid4().hex)
            evento = str(dados.get("evento") or "mensagem")
            sala = str(dados.get("sala")) if dados.get("sala") is not None else None
            id_usuario = str(dados.get("id_usuario")) if dados.get("id_usuario") is not None else None
            id_conexao = str(dados.get("id_conexao")) if dados.get("id_conexao") is not None else None
            exigir_ack = bool(dados.get("exigir_ack", False))
            envelope = {
                "ok": True,
                "evento": evento,
                "dados": dados.get("dados", {}),
                "canal": canal,
                "sala": sala,
                "id_mensagem": id_mensagem,
                "message_id": id_mensagem,
                "ordem": int(ev.seq),
                "seq": int(ev.seq),
                "cursor": int(ev.seq),
                "exigir_ack": exigir_ack,
                "id_usuario_origem": dados.get("id_usuario_origem"),
                "id_conexao_origem": dados.get("id_conexao_origem"),
                "ts": float(dados.get("ts", time.time())),
            }
            destinos = self._selecionar_destinos_locked(canal, id_conexao=id_conexao, id_usuario=id_usuario, sala=sala)
            for d in destinos:
                d.enfileirar(envelope)
            self._registrar_historico_locked(canal, envelope)
            self._metrica_inc("entregues", float(len(destinos)))
            if exigir_ack:
                pend = self.pendencias_ack.setdefault(canal, {})
                pend[id_mensagem] = {
                    "envelope": envelope,
                    "pendentes": {d.id_conexao for d in destinos},
                    "confirmados": set(),
                    "tentativas_reenvio": 0,
                    "criado_em": float(dados.get("ts", time.time())),
                }
            return
        if tipo == "ack":
            self._confirmar_ack_locked(
                canal,
                str(dados.get("id_mensagem") or ""),
                str(dados.get("id_conexao") or ""),
                status=str(dados.get("status") or "ack"),
                propagar=False,
            )
            return
        if tipo == "reenviar":
            idm = dados.get("id_mensagem")
            self._reenviar_pendentes_locked(
                canal,
                str(idm) if idm not in {None, "", "None"} else None,
                propagar=False,
            )
