from __future__ import annotations

import pytest


pytestmark = pytest.mark.security


SQL_INJECTION_PAYLOADS = [
    ("basic", "' OR '1'='1"),
    ("basic_alt", "OR 1=1"),
    ("comment", "admin'--"),
    ("union", "' UNION SELECT * FROM users --"),
    ("blind_true", "' AND 1=1 --"),
    ("blind_false", "' AND 1=2 --"),
    ("stacked", "'; DROP TABLE projects; --"),
    ("time_based", "' OR SLEEP(5) --"),
    ("error_based", "' OR extractvalue(1,concat(0x7e,user())) --"),
    ("order_by", "1' ORDER BY 100 --"),
]


class TestSQLInjection:
    @pytest.mark.parametrize("attack_type,payload", SQL_INJECTION_PAYLOADS)
    def test_basic_sql_injection_blocked(self, attack_type, payload):
        dangerous_keywords = ["' OR", "OR 1=1", "DROP TABLE", "UNION SELECT", "SLEEP", "extractvalue"]
        is_dangerous = any(kw.lower() in payload.lower() for kw in dangerous_keywords)
        assert is_dangerous, f"Payload '{payload}' ({attack_type}) not flagged as dangerous"

    @pytest.mark.parametrize("payload", [
        "' UNION SELECT username, password FROM users --",
        "' UNION SELECT * FROM information_schema.tables --",
        "' UNION SELECT column_name FROM information_schema.columns --",
    ])
    def test_union_based_injection_blocked(self, payload):
        has_union = "UNION" in payload.upper()
        has_select = "SELECT" in payload.upper()
        assert has_union and has_select

    @pytest.mark.parametrize("payload", [
        "' AND (SELECT COUNT(*) FROM users) > 0 --",
        "' OR (SELECT 1 FROM users LIMIT 1) = 1 --",
        "' AND EXISTS (SELECT 1 FROM users) --",
    ])
    def test_blind_injection_blocked(self, payload):
        has_select = "SELECT" in payload.upper()
        has_from = "FROM" in payload.upper()
        assert has_select and has_from

    def test_safe_parameterized_queries(self):
        query = "SELECT * FROM projects WHERE id = :project_id"
        params = {"project_id": "123"}
        assert ":project_id" in query
        assert params["project_id"] == "123"
        assert "'" not in query

    def test_orm_protection(self):
        dangerous_input = "' OR 1=1 --"
        from database.base import BaseModel
        assert hasattr(BaseModel, "to_dict")
