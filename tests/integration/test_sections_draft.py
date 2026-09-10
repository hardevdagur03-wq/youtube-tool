from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestSectionsDraftIntegration:
    @pytest.mark.asyncio
    async def test_sections_assemble_into_draft(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        sections_data = [
            {"heading": "Introduction", "content": "This is the introduction section content.", "order": 0},
            {"heading": "Understanding the Basics", "content": "Basic concepts explained here.", "order": 1},
            {"heading": "Advanced Topics", "content": "Advanced content goes here.", "order": 2},
            {"heading": "Conclusion", "content": "Concluding thoughts and summary.", "order": 3},
        ]
        for s in sections_data:
            created = await service.save_section(
                project_uuid=pid, heading=s["heading"],
                content=s["content"], order=s["order"],
            )
            assert created is not None

        full_content = "\n\n".join(
            f"## {s['heading']}\n\n{s['content']}" for s in sections_data
        )

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content=full_content,
            word_count=len(full_content.split()),
        )
        assert draft is not None
        assert draft["draft_number"] == 1
        assert draft["word_count"] > 0

    @pytest.mark.asyncio
    async def test_draft_preserves_section_structure(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        sections_data = [
            {"heading": "Section One", "content": "Content one.", "order": 1},
            {"heading": "Section Two", "content": "Content two.", "order": 2},
            {"heading": "Section Three", "content": "Content three.", "order": 3},
        ]
        for s in sections_data:
            await service.save_section(
                project_uuid=pid, heading=s["heading"],
                content=s["content"], order=s["order"],
            )

        sections = sorted(sections_data, key=lambda x: x["order"])
        draft_md = ""
        for s in sections:
            draft_md += f"## {s['heading']}\n\n{s['content']}\n\n"

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content=draft_md.strip(),
            word_count=len(draft_md.split()),
        )
        assert draft is not None
        assert "Section One" in draft["markdown_content"]
        assert "Section Two" in draft["markdown_content"]
        assert "Section Three" in draft["markdown_content"]

    @pytest.mark.asyncio
    async def test_heading_normalization(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        sections_data = [
            {"heading": "  Introduction  ", "content": "Intro.", "order": 0},
            {"heading": "WHAT IS PYTHON?", "content": "Definition.", "order": 1},
            {"heading": "How To Install Python", "content": "Steps.", "order": 2},
        ]
        for s in sections_data:
            created = await service.save_section(
                project_uuid=pid, heading=s["heading"].strip(),
                content=s["content"], order=s["order"],
            )
            assert created is not None
            assert created["heading"] == s["heading"].strip()

    @pytest.mark.asyncio
    async def test_toc_generation_from_sections(self, service, test_project_data):
        proj = await service.create_project(
            url=test_project_data["url"],
            video_id=test_project_data["video_id"],
        )
        pid = proj["project_id"]

        sections_data = [
            {"heading": "Getting Started", "content": "Start here.", "order": 0},
            {"heading": "Installation Guide", "content": "Install steps.", "order": 1},
            {"heading": "Configuration", "content": "Config details.", "order": 2},
            {"heading": "Usage Examples", "content": "Examples.", "order": 3},
            {"heading": "Troubleshooting", "content": "Fix issues.", "order": 4},
        ]
        for s in sections_data:
            await service.save_section(
                project_uuid=pid, heading=s["heading"],
                content=s["content"], order=s["order"],
            )

        toc_lines = [f"- [{s['heading']}](#{s['heading'].lower().replace(' ', '-')})" for s in sections_data]
        toc = "# Table of Contents\n\n" + "\n".join(toc_lines)

        draft = await service.save_draft(
            project_uuid=pid, draft_number=1,
            markdown_content=toc + "\n\n" + "\n\n".join(
                f"## {s['heading']}\n\n{s['content']}" for s in sections_data
            ),
            word_count=50,
        )
        assert draft is not None
        assert "Table of Contents" in draft["markdown_content"]
        for s in sections_data:
            assert s["heading"] in draft["markdown_content"]
