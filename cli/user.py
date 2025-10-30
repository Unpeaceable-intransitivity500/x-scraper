import asyncio
from typing import Optional

import click

from .utils import run_scraper_command, parse_analysis_types, save_result_with_analysis


@click.command()
@click.option('--username', '-u', required=True, help='Twitter username (without @)')
@click.option('--count', '-n', default=50, help='Number of tweets to retrieve')
@click.option('--analyze/--no-analyze', default=True, help='Perform AI analysis')
@click.option('--analysis-types', '-a', default='sentiment,topics,summary', help='Analysis types (comma-separated)')
@click.option('--resume', '-r', is_flag=True, help='Resume from last checkpoint')
@click.option('--session-limit', '-s', type=int, help='Max tweets per session (e.g., 800). Use with --resume for batched scraping')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def user(ctx: click.Context, username: str, count: int, analyze: bool, 
         analysis_types: str, resume: bool, session_limit: Optional[int], 
         output: Optional[str]) -> None:
    
    async def run_user_scrape(scraper) -> None:
        analysis_list = parse_analysis_types(analysis_types)
        
        if resume:
            click.echo("Resuming from last checkpoint...")
        if session_limit:
            click.echo(f"Session limit: {session_limit} tweets per session")
        
        result = await scraper.scrape_user_tweets(
            username=username,
            count=count,
            analyze=analyze,
            analysis_types=analysis_list,
            unlimited_history=True,
            browser_mode=True,
            resume=resume,
            max_tweets_per_session=session_limit
        )
        
        if output:
            save_result_with_analysis(result, output)
            click.echo(f"Found {result.get('tweet_count', 0)} tweets from @{username}")
        else:
            click.echo(f"Found {result.get('tweet_count', 0)} tweets from @{username}")
            if result.get('analysis'):
                click.echo("AI analysis completed")
    
    asyncio.run(run_scraper_command(
        ctx.obj['config'],
        run_user_scrape,
        "User scraping failed"
    ))
