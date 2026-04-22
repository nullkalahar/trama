"""Modelo de configuração do WebApp da Trama."""

from __future__ import annotations

from dataclasses import dataclass, field, fields


@dataclass
class ConfiguracaoWebApp:
    cors_enabled: bool = False
    cors_origin: str = "*"
    cors_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_headers: str = "Content-Type,Authorization"
    health_path: str = "/saude"
    readiness_path: str = "/pronto"
    liveness_path: str = "/vivo"
    health_enabled: bool = True
    static_prefix: str | None = None
    static_dir: object | None = None
    api_versions: set[str] = field(default_factory=set)
    contratos_http: dict[str, dict[str, object]] = field(default_factory=dict)
    observabilidade_ativa: bool = False
    observabilidade_path: str = "/observabilidade"
    alertas_path: str = "/alertas"
    metricas_path: str = "/metricas"
    otlp_path: str = "/otlp-json"
    alertas_config: dict[str, object] = field(default_factory=dict)
    ambiente: str = "dev"
    cors_origens_por_ambiente: dict[str, list[str]] = field(
        default_factory=lambda: {
            "dev": ["*"],
            "teste": ["http://localhost", "http://127.0.0.1"],
            "producao": [],
        }
    )
    seguranca_http_headers: dict[str, str] = field(
        default_factory=lambda: {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "X-Permitted-Cross-Domain-Policies": "none",
        }
    )
    csp_por_ambiente: dict[str, str] = field(
        default_factory=lambda: {
            "dev": "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; connect-src *;",
            "teste": "default-src 'self' 'unsafe-inline' data: blob:; connect-src 'self';",
            "producao": "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';",
        }
    )
    auditoria_admin_ativa: bool = True
    engine_http_preferida: str = "legada"
    engine_http_fallback_automatico: bool = True
    shutdown_gracioso_segundos: float = 5.0
    limites_operacionais_por_engine: dict[str, dict[str, object]] = field(
        default_factory=lambda: {
            "legada": {
                "max_body_bytes": 5 * 1024 * 1024,
                "timeout_leitura_segundos": 15.0,
            },
            "asgi": {
                "max_body_bytes": 8 * 1024 * 1024,
                "timeout_leitura_segundos": 20.0,
            },
        }
    )


def aplicar_configuracao_web_app(destino: object, cfg: ConfiguracaoWebApp) -> None:
    """Aplica todos os campos de configuração no objeto de destino."""
    for f in fields(cfg):
        setattr(destino, f.name, getattr(cfg, f.name))
