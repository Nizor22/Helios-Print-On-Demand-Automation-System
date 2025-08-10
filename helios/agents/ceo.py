from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger

from ..config import HeliosConfig
from ..mcp_client import MCPClient
from ..utils.history import record_action
from .zeitgeist import discover_trend, TrendData
from .ethics import screen_ethics
from .audience import analyze_audience, AudienceInsights
from .product import select_products, ProductSelection
from .creative import generate_designs, CreativeBatch
from .marketing import write_listings, MarketingBatch
from .publish import plan_publication, PublicationPlan


@dataclass
class ExecutionSummary:
    total_time_seconds: float
    agents_used: int
    parallel_executions: int
    quality_scores: dict[str, Any]


@dataclass
class CEOResult:
    execution_summary: ExecutionSummary
    trend_data: TrendData
    audience_insights: AudienceInsights
    product_portfolio: list[dict[str, Any]]
    creative_concepts: list[dict[str, Any]]
    marketing_materials: list[dict[str, Any]]
    publication_queue: list[dict[str, Any]]


async def run_ceo(config: HeliosConfig, dry_run: bool = False) -> CEOResult:
    mcp = MCPClient.from_env(config.mcp_server_url, config.mcp_auth_token)

    # High priority: trend discovery with quality gates
    trend = await discover_trend(mcp, timeout_s=30.0, dry_run=dry_run)
    ethics = await screen_ethics(trend.trend_name, trend.keywords, dry_run=dry_run)

    if trend.velocity in {"declining", "flat"} or trend.opportunity_score < config.min_opportunity_score:
        raise RuntimeError("Trend does not meet opportunity/velocity requirements. Re-discover.")
    if ethics.status in {"high_risk", "critical"}:
        raise RuntimeError("Ethics gate failed. Re-discover.")

    # Contextual decision rules
    rapid_mode = False
    if trend.urgency_level == "immediate" and trend.opportunity_score >= 8.5:
        rapid_mode = True

    # Parallel analysis: audience + product
    audience_task = asyncio.create_task(analyze_audience(trend.__dict__, rapid=rapid_mode, dry_run=dry_run))
    product_task = asyncio.create_task(select_products({}, dry_run=dry_run))
    audience, product = await asyncio.gather(audience_task, product_task)

    if audience.confidence_score < config.min_audience_confidence:
        raise RuntimeError("Audience confidence below threshold")

    # Batch creative + marketing
    creative = await generate_designs(product.selected_products, audience.primary_persona, dry_run=dry_run)
    marketing = await write_listings(creative.design_batch, trend.trend_name, dry_run=dry_run)
    publication = await plan_publication(marketing.listings, config=config, dry_run=dry_run)

    exec_summary = ExecutionSummary(
        total_time_seconds=180.0 if dry_run else 0.0,
        agents_used=6,
        parallel_executions=2,
        quality_scores={
            "ethics": ethics.status,
            "audience_confidence": audience.confidence_score,
            "trend_opportunity": trend.opportunity_score,
        },
    )

    result = CEOResult(
        execution_summary=exec_summary,
        trend_data=trend,
        audience_insights=audience,
        product_portfolio=product.selected_products,
        creative_concepts=creative.design_batch,
        marketing_materials=marketing.listings,
        publication_queue=publication.publication_queue,
    )

    # Record the action in history
    record_action(
        command="run",
        parameters={"dry_run": dry_run},
        result_summary={
            "trend": trend.trend_name,
            "opportunity_score": trend.opportunity_score,
            "audience_confidence": audience.confidence_score,
            "products_selected": len(product.selected_products),
            "designs_created": len(creative.design_batch),
            "listings_created": len(marketing.listings),
            "items_queued": len(publication.publication_queue),
        },
        dry_run=dry_run,
        success=True
    )

    return result
