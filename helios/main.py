from __future__ import annotations

import asyncio
from dataclasses import asdict

import typer
from rich import print
from rich.panel import Panel
from rich.table import Table

from .config import HeliosConfig
from .agents.ceo import run_ceo
from .utils.jsonio import dumps
from .utils.history import get_last_action, get_recent_actions, record_action
from .mcp_stub import serve as mcp_serve
from .providers.etsy import EtsyClient

app = typer.Typer(add_completion=False)


@app.command()
def run(dry_run: bool = typer.Option(False, help="Run with mock data")) -> None:
    config = HeliosConfig.load()
    try:
        result = asyncio.run(run_ceo(config, dry_run=dry_run))
    except Exception as e:
        print(Panel.fit(f"[red]Execution failed[/red]\n{e}"))
        # Record failure in history
        record_action(
            command="run",
            parameters={"dry_run": dry_run},
            result_summary={},
            dry_run=dry_run,
            success=False,
            error=str(e)
        )
        raise typer.Exit(code=1)

    print(Panel.fit("Helios CEO Result (truncated)"))
    summary = {
        "execution_summary": asdict(result.execution_summary),
        "trend_data": asdict(result.trend_data),
        "audience_insights": asdict(result.audience_insights),
        "product_portfolio": result.product_portfolio,
        "creative_concepts": result.creative_concepts[:1],
        "marketing_materials": result.marketing_materials[:2],
        "publication_queue": result.publication_queue[:2],
    }
    print(dumps(summary))


@app.command()
def repeat() -> None:
    """Repeat the last executed action"""
    last_action = get_last_action()
    
    if not last_action:
        print(Panel.fit("[yellow]No previous action found in history[/yellow]"))
        raise typer.Exit(code=1)
    
    print(Panel.fit(f"[blue]Repeating last action:[/blue]\n"
                    f"Command: {last_action.command}\n"
                    f"Timestamp: {last_action.timestamp}\n"
                    f"Parameters: {dumps(last_action.parameters)}"))
    
    # Currently only supporting repeat of 'run' command
    if last_action.command == "run":
        run(dry_run=last_action.parameters.get("dry_run", False))
    else:
        print(Panel.fit(f"[red]Repeat not implemented for command: {last_action.command}[/red]"))
        raise typer.Exit(code=1)


@app.command()
def history(limit: int = typer.Option(10, help="Number of recent actions to show")) -> None:
    """Show recent action history"""
    recent_actions = get_recent_actions(limit)
    
    if not recent_actions:
        print(Panel.fit("[yellow]No actions found in history[/yellow]"))
        return
    
    table = Table(title="Recent Action History")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Dry Run", style="yellow")
    table.add_column("Success", style="white")
    table.add_column("Details", style="blue")
    
    for action in recent_actions:
        details = []
        if action.success and action.result_summary:
            if "trend" in action.result_summary:
                details.append(f"Trend: {action.result_summary['trend']}")
            if "opportunity_score" in action.result_summary:
                details.append(f"Score: {action.result_summary['opportunity_score']}")
        elif action.error:
            details.append(f"Error: {action.error[:50]}...")
        
        table.add_row(
            action.timestamp,
            action.command,
            "Yes" if action.dry_run else "No",
            "✓" if action.success else "✗",
            " | ".join(details) if details else "-"
        )
    
    print(table)


@app.command()
def demo() -> None:
    print("See README for usage")


@app.command()
def mcp_stub(host: str = "127.0.0.1", port: int = 8787) -> None:
    print(Panel.fit(f"Starting MCP stub on http://{host}:{port}"))
    try:
        mcp_serve(host=host, port=port)
    except KeyboardInterrupt:
        print("Shutting down MCP stub")


def _etsy_from_env(cfg: HeliosConfig) -> EtsyClient:
    if not cfg.etsy_api_key:
        raise typer.BadParameter("ETSY_API_KEY is required in .env")
    if not cfg.etsy_oauth_token:
        raise typer.BadParameter("ETSY_OAUTH_TOKEN is required in .env")
    return EtsyClient(api_key=cfg.etsy_api_key, oauth_token=cfg.etsy_oauth_token)


@app.command()
def etsy_me() -> None:
    cfg = HeliosConfig.load()
    client = _etsy_from_env(cfg)
    data = asyncio.run(client.get_me())
    print(dumps(data))


@app.command()
def etsy_shops() -> None:
    cfg = HeliosConfig.load()
    client = _etsy_from_env(cfg)
    me = asyncio.run(client.get_me())
    user_id = me.get("user_id") or me.get("shop_id") or me.get("id")
    if not user_id:
        raise typer.Exit(code=1)
    data = asyncio.run(client.get_shops_by_user(int(user_id)))
    print(dumps(data))


@app.command()
def etsy_taxonomy(kind: str = typer.Option("buyer", help="buyer|seller")) -> None:
    cfg = HeliosConfig.load()
    client = _etsy_from_env(cfg)
    if kind == "buyer":
        data = asyncio.run(client.get_buyer_taxonomy_nodes())
    else:
        data = asyncio.run(client.get_seller_taxonomy_nodes())
    print(dumps(data))


@app.command()
def etsy_shipping_profiles(shop_id: str = typer.Option("", help="Override shop id")) -> None:
    cfg = HeliosConfig.load()
    client = _etsy_from_env(cfg)
    sid = int(shop_id or (cfg.etsy_shop_id or 0))
    if not sid:
        print("Missing shop_id. Provide --shop-id or set ETSY_SHOP_ID in .env")
        raise typer.Exit(code=1)
    data = asyncio.run(client.get_shipping_profiles(sid))
    print(dumps(data))


@app.command()
def etsy_return_policies(shop_id: str = typer.Option("", help="Override shop id")) -> None:
    cfg = HeliosConfig.load()
    client = _etsy_from_env(cfg)
    sid = int(shop_id or (cfg.etsy_shop_id or 0))
    if not sid:
        print("Missing shop_id. Provide --shop-id or set ETSY_SHOP_ID in .env")
        raise typer.Exit(code=1)
    data = asyncio.run(client.get_return_policies(sid))
    print(dumps(data))

if __name__ == "__main__":
    app()
