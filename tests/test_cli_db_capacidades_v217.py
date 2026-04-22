from __future__ import annotations

import json
from pathlib import Path

from trama import cli


def test_cli_db_capacidades_json_sqlite(tmp_path: Path, capsys) -> None:
    dsn = f"sqlite:///{tmp_path / 'v217_cli.db'}"
    rc = cli.main(["db-capacidades", "--dsn", dsn, "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["backend"] == "sqlite"
    assert payload["dialeto_sql"] == "sqlite"
