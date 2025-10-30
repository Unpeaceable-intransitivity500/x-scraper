import asyncio
import sys
from pathlib import Path
from typing import Optional, Set
from datetime import datetime

import click

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src.date_utils import parse_date_or_relative, generate_date_ranges

from .utils import run_scraper_command, parse_analysis_types, save_result_with_analysis


async def scrape_date_ranges(
    scraper,
    username: str,
    date_ranges: list,
    max_tweets: int,
    delay_between_ranges: int
) -> tuple[list, Set[str]]:
    """Scrape tweets across multiple date ranges and deduplicate.
    
    Returns:
        Tuple of (all_tweets, existing_tweet_ids)
    """
    all_tweets = []
    existing_tweet_ids = set()
    
    for idx, (range_start, range_end) in enumerate(date_ranges, 1):
        click.echo(f"\n[{idx}/{len(date_ranges)}] Scraping {range_start} to {range_end}...")
        
        result = await scraper.scrape_user_tweets_by_search(
            username=username,
            since_date=range_start,
            until_date=range_end,
            max_tweets_per_range=max_tweets,
            existing_tweet_ids=existing_tweet_ids
        )
        
        new_tweets = result.get('tweets', [])
        click.echo(f"  ✓ Collected {len(new_tweets)} tweets from this range")
        
        for tweet in new_tweets:
            tweet_id = tweet.get('id')
            if tweet_id and tweet_id not in existing_tweet_ids:
                all_tweets.append(tweet)
                existing_tweet_ids.add(tweet_id)
        
        click.echo(f"  Total unique tweets so far: {len(all_tweets)}")
        
        if idx < len(date_ranges):
            click.echo(f"  Waiting {delay_between_ranges}s before next range...")
            await asyncio.sleep(delay_between_ranges)
    
    return all_tweets, existing_tweet_ids


@click.command(name='search-historical')
@click.option('--username', '-u', required=True, help='Twitter username (without @)')
@click.option('--since', '-s', required=True, help='Start date (YYYY-MM-DD or relative like "6months")')
@click.option('--until', '-U', help='End date (YYYY-MM-DD). Defaults to today')
@click.option('--chunk-type', '-c', type=click.Choice(['weekly', 'monthly', 'quarterly']), default='monthly', help='Date range chunk size')
@click.option('--max-per-range', '-m', type=int, help='Max tweets per date range')
@click.option('--analyze/--no-analyze', default=False, help='Perform AI analysis')
@click.option('--analysis-types', '-a', default='sentiment,topics,summary', help='Analysis types (comma-separated)')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def search_historical(ctx: click.Context, username: str, since: str, until: Optional[str], 
                     chunk_type: str, max_per_range: Optional[int], analyze: bool, 
                     analysis_types: str, output: Optional[str]) -> None:
    """Scrape historical tweets using advanced search with date ranges."""
    
    async def run_historical_search(scraper) -> None:
        since_date = parse_date_or_relative(since)
        until_date = until if until else datetime.now().strftime('%Y-%m-%d')
        
        click.echo(f"\nSearching historical tweets for @{username}")
        click.echo(f"Date range: {since_date} to {until_date}")
        click.echo(f"Chunk type: {chunk_type}")
        
        date_ranges = generate_date_ranges(since_date, until_date, chunk_type)
        click.echo(f"Generated {len(date_ranges)} date ranges to scrape")
        
        search_config = scraper.config_manager.get_search_settings()
        max_tweets = max_per_range or search_config['max_tweets_per_date_range']
        delay_between_ranges = search_config['search_delay_between_ranges']
        
        all_tweets, _ = await scrape_date_ranges(
            scraper, username, date_ranges, max_tweets, delay_between_ranges
        )
        
        click.echo(f"\n✓ Historical search complete!")
        click.echo(f"Total unique tweets collected: {len(all_tweets)}")
        
        final_result = {
            'username': username,
            'tweet_count': len(all_tweets),
            'unique_tweet_count': len(all_tweets),
            'tweets': all_tweets,
            'date_range': {'since': since_date, 'until': until_date},
            'chunk_type': chunk_type,
            'ranges_scraped': len(date_ranges)
        }
        
        if analyze and all_tweets:
            click.echo("\nRunning AI analysis...")
            analysis_list = parse_analysis_types(analysis_types)
            analysis_result = await scraper._analyze_tweets(all_tweets, analysis_types=analysis_list)
            final_result['analysis'] = analysis_result
            click.echo("✓ AI analysis completed")
        
        if output:
            output_path = output
        else:
            output_dir = scraper.config_manager.get_scraping_settings()['output_directory']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            since_safe = since_date.replace('-', '')
            until_safe = until_date.replace('-', '')
            output_path = f"{output_dir}/{username}/tweets_{username}_historical_{since_safe}_to_{until_safe}_{timestamp}.json"
        
        save_result_with_analysis(final_result, output_path)
        click.echo(f"\n✓ Results saved to {output_path}")
    
    asyncio.run(run_scraper_command(
        ctx.obj['config'],
        run_historical_search,
        "Historical search failed"
    ))
