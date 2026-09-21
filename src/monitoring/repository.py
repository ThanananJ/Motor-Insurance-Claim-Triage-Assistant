"""SQLite persistence for allow-listed runtime monitoring events."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import MonitoringEvent, MonitoringFilter


class MonitoringRepository:
    def __init__(self, db_path: str | Path = "data/runtime_monitoring.db") -> None:
        self.db_path = str(db_path)

    def initialize(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_events (
                    event_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL,
                    app_version TEXT, model_provider TEXT, model_name TEXT,
                    prompt_version TEXT, policy_version TEXT, output_strategy TEXT,
                    status TEXT, stage TEXT, latency_ms REAL, provider_status TEXT,
                    provider_error_category TEXT, schema_valid INTEGER,
                    validation_error_category TEXT, fallback_triggered INTEGER NOT NULL,
                    fallback_reason TEXT, retry_count INTEGER NOT NULL,
                    input_tokens INTEGER, output_tokens INTEGER,
                    token_usage_available INTEGER NOT NULL,
                    claim_scenario_category TEXT, ai_facts_proposed_count INTEGER,
                    ai_unknown_count INTEGER, human_confirmed INTEGER NOT NULL,
                    human_override INTEGER NOT NULL, override_field_count INTEGER NOT NULL,
                    changed_field_categories TEXT, override_reason_category TEXT,
                    coverage_status TEXT, route TEXT, missing_document_count INTEGER,
                    risk_signal_count INTEGER, late_submission_flag INTEGER,
                    human_final_decision_recorded INTEGER NOT NULL,
                    human_final_decision_category TEXT
                )
            """)
            existing = {row[1] for row in connection.execute("PRAGMA table_info(monitoring_events)")}
            migrations = {
                "prompt_name": "TEXT", "tokenizer_name": "TEXT", "token_count_source": "TEXT",
                "token_count_available": "INTEGER NOT NULL DEFAULT 0", "prompt_token_count": "INTEGER",
                "token_count_error_category": "TEXT", "model_capability_context_tokens": "INTEGER",
                "effective_context_window_tokens": "INTEGER", "reserved_output_tokens": "INTEGER",
                "max_prompt_tokens": "INTEGER", "remaining_prompt_capacity_tokens": "INTEGER",
                "context_usage_percent": "REAL", "context_status": "TEXT",
                "over_prompt_limit": "INTEGER", "context_source": "TEXT",
            }
            for column, definition in migrations.items():
                if column not in existing:
                    connection.execute(f"ALTER TABLE monitoring_events ADD COLUMN {column} {definition}")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_request ON monitoring_events(request_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_time ON monitoring_events(timestamp_utc)")

    def insert(self, event: MonitoringEvent) -> bool:
        self.initialize()
        values = event.model_dump(mode="json")
        columns = list(values)
        sql = f"INSERT OR IGNORE INTO monitoring_events ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute(sql, [values[column] for column in columns])
            return cursor.rowcount == 1

    def query(self, filters: MonitoringFilter | None = None) -> list[dict]:
        self.initialize()
        filters = filters or MonitoringFilter()
        clauses, params = [], []
        mapping = {
            "environment": filters.environment, "model_name": filters.model_name,
            "prompt_version": filters.prompt_version, "status": filters.status,
            "prompt_name": filters.prompt_name,
            "provider_error_category": filters.error_category,
            "claim_scenario_category": filters.scenario_category,
            "route": filters.route, "coverage_status": filters.coverage_status,
        }
        for column, value in mapping.items():
            if value and value != "All":
                clauses.append(f"{column} = ?")
                params.append(value)
        if filters.request_id_prefix and filters.request_id_prefix.strip():
            clauses.append("request_id LIKE ?")
            params.append(filters.request_id_prefix.strip() + "%")
        if filters.synthetic is not None:
            clauses.append("is_synthetic = ?")
            params.append(int(filters.synthetic))
        if filters.start_utc:
            clauses.append("timestamp_utc >= ?")
            params.append(filters.start_utc.isoformat())
        if filters.end_utc:
            clauses.append("timestamp_utc <= ?")
            params.append(filters.end_utc.isoformat())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("SELECT * FROM monitoring_events" + where + " ORDER BY timestamp_utc", params)]

    def delete_synthetic(self) -> int:
        self.initialize()
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.execute("DELETE FROM monitoring_events WHERE is_synthetic = 1")
            return cursor.rowcount
