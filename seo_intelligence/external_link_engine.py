"""External Link Engine — suggests external authority sources for citations.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import ExternalLink

logger = logging.getLogger(__name__)


class ExternalLinkEngine:
    """Generates external linking suggestions based on content topic."""

    # Domain authority mapping by topic cluster
    AUTHORITY_DOMAINS: dict[str, list[dict]] = {
        "technology": [
            {"domain": "docs.example.com", "reason": "Official documentation", "type": "documentation", "authority": 0.9},
            {"domain": "github.com", "reason": "Open source code repositories", "type": "source_code", "authority": 0.8},
        ],
        "ai_ml": [
            {"domain": "arxiv.org", "reason": "Academic research papers", "type": "research", "authority": 0.9},
            {"domain": "paperswithcode.com", "reason": "ML research with code", "type": "research", "authority": 0.8},
        ],
        "data": [
            {"domain": "kaggle.com", "reason": "Data science resources", "type": "community", "authority": 0.7},
            {"domain": "towardsdatascience.com", "reason": "Data science articles", "type": "blog", "authority": 0.6},
        ],
        "development": [
            {"domain": "developer.mozilla.org", "reason": "Web development documentation", "type": "documentation", "authority": 0.9},
            {"domain": "stackoverflow.com", "reason": "Developer Q&A community", "type": "community", "authority": 0.7},
        ],
        "business": [
            {"domain": "hbr.org", "reason": "Business research and insights", "type": "research", "authority": 0.8},
            {"domain": "forbes.com", "reason": "Business news and analysis", "type": "news", "authority": 0.7},
        ],
        "security": [
            {"domain": "owasp.org", "reason": "Web security standards", "type": "standard", "authority": 0.9},
            {"domain": "nist.gov", "reason": "Government security standards", "type": "standard", "authority": 0.9},
        ],
        "cloud": [
            {"domain": "aws.amazon.com", "reason": "Cloud computing documentation", "type": "documentation", "authority": 0.8},
            {"domain": "cloud.google.com", "reason": "Google Cloud documentation", "type": "documentation", "authority": 0.8},
        ],
    }

    def generate(
        self,
        knowledge_graph: dict[str, Any] | None,
        primary_keyword: str = "",
    ) -> list[ExternalLink]:
        links: list[ExternalLink] = []
        seen_domains: set[str] = set()
        kg = knowledge_graph or {}

        if not isinstance(kg, dict):
            return links

        clusters = kg.get("semantic_clusters", [])
        if isinstance(clusters, list):
            for cluster in clusters:
                if isinstance(cluster, dict):
                    name = cluster.get("name", "")
                    domains = self.AUTHORITY_DOMAINS.get(name, [])
                    for d in domains:
                        domain = d["domain"]
                        if domain not in seen_domains:
                            seen_domains.add(domain)
                            links.append(ExternalLink(
                                suggested_domain=domain,
                                url_pattern=f"https://{domain}",
                                reason=d["reason"],
                                authority_score=d["authority"],
                                reference_type=d["type"],
                                priority=int(d["authority"] * 10),
                            ))

        if not links:
            links.append(ExternalLink(
                suggested_domain="wikipedia.org",
                url_pattern="https://wikipedia.org",
                reason="General reference for background information",
                authority_score=0.7,
                reference_type="reference",
                priority=5,
            ))

        return links
