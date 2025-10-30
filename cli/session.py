import asyncio

import click

from .utils import run_scraper_command


@click.command()
@click.pass_context
def refresh_session(ctx: click.Context) -> None:
    """Refresh the Twitter session by logging in again."""
    
    async def run_session_refresh(scraper) -> None:
        success = await scraper.refresh_twitter_session()
        if success:
            click.echo("Twitter session refreshed successfully!")
        else:
            click.echo("Failed to refresh Twitter session")
    
    asyncio.run(run_scraper_command(
        ctx.obj['config'],
        run_session_refresh,
        "Session refresh failed"
    ))
