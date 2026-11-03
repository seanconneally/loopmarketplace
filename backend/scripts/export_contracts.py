"""Export OpenAPI and the initial DDL snapshot before the first migration is released."""

import json
import sys
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app import models  # noqa: F401
from app.core.db import Base
from app.main import app
from app.ws_schemas import WebSocketEvent

project = Path(__file__).resolve().parents[2]
(project / "docs/openapi.json").write_text(
    json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8"
)
(project / "docs/websocket-events.schema.json").write_text(
    json.dumps(TypeAdapter(WebSocketEvent).json_schema(), indent=2) + "\n", encoding="utf-8"
)
if "--initial-schema" in sys.argv or "--schema" in sys.argv:
    dialect = postgresql.dialect()
    statements = [
        "-- Initial schema snapshot. Do not regenerate after release.\nCREATE EXTENSION IF NOT EXISTS postgis;"
    ]
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    ddl = "\n\n".join(statements) + "\n"
    (project / "docs/schema.sql").write_text(ddl, encoding="utf-8")
    if "--initial-schema" in sys.argv:
        (project / "backend/alembic/versions/0001_initial.sql").write_text(ddl, encoding="utf-8")
