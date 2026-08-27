from __future__ import annotations

from typing import Any

from authstatus_api.audit.tables import initialize_audit_tables
from authstatus_api.authorizations.tables import initialize_authorization_tables
from authstatus_api.governance.tables import initialize_governance_tables
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.migration_runner import run_registered_migrations
from authstatus_api.registered_options.tables import (
    initialize_registered_options_table,
)
from authstatus_api.security.tables import initialize_security_tables


def initialize_schema(conn: Any) -> None:
    initialize_authorization_tables(conn)
    initialize_security_tables(conn)
    initialize_governance_tables(conn)
    initialize_audit_tables(conn)
    initialize_registered_options_table(conn)
    run_registered_migrations(conn)


def init_db() -> None:
    conn = get_conn()

    try:
        initialize_schema(conn)
        conn.commit()
    finally:
        conn.close()
