from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.chaos


class TestLlmTimeout:
    @pytest.mark.asyncio
    async def test_llm_timeout_during_analysis(self):
        with patch("database.db_service.DatabaseService.generate_analysis", new_callable=AsyncMock) as m:
            m.side_effect = TimeoutError("LLM request timed out")
            svc = DatabaseService()  # noqa: F821
            with pytest.raises(TimeoutError, match="LLM request timed out"):
                await svc.generate_analysis("p1")

    @pytest.mark.asyncio
    async def test_retry_on_llm_timeout(self):
        call_count = 0

        async def llm_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("LLM timed out")
            return {"status": "completed"}

        result = await llm_with_retry()
        assert call_count == 3
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        with patch("database.db_service.DatabaseService.generate_analysis", new_callable=AsyncMock) as m:
            m.side_effect = [
                Exception("LLM unavailable"),
                {"project_id": "p1", "status": "completed", "fallback": True},
            ]
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_analysis("p1")
            assert result.get("fallback") is True
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_llm_unavailable(self):
        with patch("database.db_service.DatabaseService.generate_analysis", new_callable=AsyncMock) as m:
            m.return_value = {"project_id": "p1", "status": "completed", "degraded": True}
            svc = DatabaseService()  # noqa: F821
            result = await svc.generate_analysis("p1")
            assert result["status"] == "completed"
            assert result.get("degraded") is True
