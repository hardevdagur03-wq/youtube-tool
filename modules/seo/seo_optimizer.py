"""SEO Optimizer — Phase 8. Core orchestration of all SEO analysis modules."""

from __future__ import annotations
import logging
from typing import Any

from models.blog_generation import BlogResult, FAQItem
from models.seo_package import SEOPackage, KeywordDensity, KeywordAnalysis, HeadingAnalysis, HeadingInfo
from models.seo_package import LinkSuggestion, ImageSEO, OpenGraph, TwitterCard, SchemaMarkup, ReadabilityAnalysis, SEOStatistics, Recommendation

from modules.seo.slug_generator import from_blog as gen_slug
from modules.seo.meta_generator import generate_meta
from modules.seo.keyword_analyzer import analyze as kw_analyze
from modules.seo.heading_optimizer import analyze as heading_analyze
from modules.seo.link_recommender import suggest_internal, suggest_external
from modules.seo.schema_generator import generate as gen_schema
from modules.seo.social_metadata import generate_all as gen_social
from modules.seo.readability import analyze as read_analyze
from modules.seo.seo_score import compute as compute_seo_score
from modules.seo.recommendation_engine import generate as gen_recs
from modules.ai.provider import LLMProvider

logger = logging.getLogger(__name__)


def optimize(
    blog: BlogResult,
    video_id: str = "",
    primary_keyword: str = "",
    secondary_keywords: list[str] | None = None,
    long_tail_keywords: list[str] | None = None,
    lsi_keywords: list[str] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    provider: LLMProvider | None = None,
) -> SEOPackage:
    """Run the full SEO optimization pipeline."""
    pk = primary_keyword or blog.seo_title.split()[0] if blog.seo_title else ""
    sec = secondary_keywords or []
    lt = long_tail_keywords or []
    lsi = lsi_keywords or []
    tg = tags or []

    kw_data = kw_analyze(blog, pk, sec, lt, lsi)
    heading_data = heading_analyze(blog, pk)
    internal = [LinkSuggestion(**l) for l in suggest_internal(blog)]
    external = [LinkSuggestion(**l) for l in suggest_external(blog)]
    schema = gen_schema(blog, video_id, pk, tg, metadata, provider)
    social = gen_social(blog, pk)
    readability = read_analyze(blog)
    scores = compute_seo_score(blog, pk, kw_data)
    recs = gen_recs(blog, scores, kw_data)
    meta = generate_meta(blog.seo_title, pk, sec, blog.seo_title, "", "", provider)

    density = KeywordDensity(
        primary=kw_data.get("density", {}).get("primary", 0.0),
        secondary=kw_data.get("density", {}).get("secondary", {}),
    )
    kw_analysis = KeywordAnalysis(
        primary=pk,
        secondary=sec,
        long_tail=lt,
        lsi=lsi,
        density=density,
        in_title=kw_data.get("in_title", False),
        in_meta=kw_data.get("in_meta", False),
        in_intro=kw_data.get("in_intro", False),
        in_headings=kw_data.get("in_headings", []),
        in_first_paragraph=kw_data.get("in_first_paragraph", False),
        in_last_paragraph=kw_data.get("in_last_paragraph", False),
    )

    headings = HeadingAnalysis(
        h1_count=heading_data.get("h1_count", 0),
        h2_count=heading_data.get("h2_count", 0),
        h3_count=heading_data.get("h3_count", 0),
        headings=[HeadingInfo(**h) for h in heading_data.get("headings", [])],
        issues=heading_data.get("issues", []),
    )

    return SEOPackage(
        meta_title=meta.get("meta_title", blog.seo_title[:60]),
        meta_description=meta.get("meta_description", blog.meta_description or blog.introduction[:160]),
        slug=gen_slug(blog.seo_title, pk, "blog-post"),
        canonical_url=f"https://youtube.com/watch?v={video_id}" if video_id else "",
        keywords=kw_analysis,
        headings=headings,
        internal_links=internal,
        external_links=external,
        image=ImageSEO(
            alt_text=f"{blog.seo_title[:120]}" if blog.seo_title else "",
            title=blog.seo_title[:200] if blog.seo_title else "",
            suggested_filename=blog.slug.replace("-", "_")[:80] + ".webp" if blog.slug else "blog-image.webp",
        ),
        open_graph=OpenGraph(**social.get("open_graph", {})),
        twitter_card=TwitterCard(**social.get("twitter_card", {})),
        schema_markup=SchemaMarkup(**schema),
        readability=ReadabilityAnalysis(**readability),
        statistics=SEOStatistics(
            word_count=readability.get("word_count", 0),
            reading_time=readability.get("reading_time", "< 1 min"),
            seo_score=scores.get("score", 0.0),
        ),
        recommendations=[Recommendation(**r) for r in recs],
    )
