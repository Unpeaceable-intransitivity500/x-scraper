import asyncio
from typing import Optional

import click

from .utils import (
    run_scraper_command,
    parse_analysis_types,
    generate_output_paths,
    save_result_with_analysis
)


@click.command()
@click.option('--query', '-q', required=True, help='Search query')
@click.option('--count', '-n', default=50, help='Number of tweets to retrieve')
@click.option('--type', '-t', default='Latest', type=click.Choice(['Latest', 'Top', 'Media']), help='Result type')
@click.option('--analyze/--no-analyze', default=True, help='Perform AI analysis')
@click.option('--analysis-types', '-a', default='sentiment,topics,summary', help='Analysis types (comma-separated)')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def search(ctx: click.Context, query: str, count: int, type: str, analyze: bool, 
           analysis_types: str, output: Optional[str]) -> None:
    """Search for tweets by keyword or phrase."""
    
    async def run_search(scraper) -> None:
        analysis_list = parse_analysis_types(analysis_types)
        
        result = await scraper.search_tweets(
            query=query,
            count=count,
            result_type=type,
            analyze=analyze,
            analysis_types=analysis_list
        )
        
        output_dir = scraper.config_manager.get_scraping_settings()['output_directory']
        result_path, analysis_path = generate_output_paths(
            output=output,
            output_dir=output_dir,
            identifier=query,
            subdirectory='search_results',
            has_analysis=result.get('analysis') is not None
        )
        
        save_result_with_analysis(result, result_path, analysis_path)
        click.echo(f"Found {result.get('tweet_count', 0)} tweets")
    
    asyncio.run(run_scraper_command(
        ctx.obj['config'],
        run_search,
        "Search failed"
    ))
