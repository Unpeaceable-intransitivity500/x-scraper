import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime

import click

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src import XScraper
from src.exceptions import (
    XScraperError,
    AuthenticationError,
    RateLimitError,
    BotDetectionError,
    NetworkError,
    ScrapingError
)


def parse_analysis_types(analysis_types: str) -> List[str]:
    return [t.strip() for t in analysis_types.split(',') if t.strip()]


def save_result_with_analysis(
    result: Dict[str, Any],
    output_path: str,
    analysis_path: Optional[str] = None
) -> None:
    if result.get('analysis') and analysis_path:
        with open(analysis_path, 'w') as f:
            json.dump(result['analysis'], f, indent=2, default=str)
        click.echo(f"AI analysis saved to {analysis_path}")
        
        result_without_analysis = {k: v for k, v in result.items() if k != 'analysis'}
    else:
        result_without_analysis = result
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result_without_analysis, f, indent=2, default=str)
    
    click.echo(f"Results saved to {output_path}")


def generate_output_paths(
    output: Optional[str],
    output_dir: str,
    identifier: str,
    subdirectory: Optional[str] = None,
    has_analysis: bool = False
) -> tuple[str, Optional[str]]:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_identifier = identifier.replace(' ', '_').replace('/', '_')[:30]
    
    if output:
        result_path = output
        if has_analysis:
            analysis_path = str(Path(output).parent / f"{Path(output).stem}_analysis{Path(output).suffix}")
        else:
            analysis_path = None
    else:
        if subdirectory:
            base_dir = Path(output_dir) / subdirectory
        else:
            base_dir = Path(output_dir) / safe_identifier
        
        base_dir.mkdir(parents=True, exist_ok=True)
        result_path = str(base_dir / f"{safe_identifier}_{timestamp}.json")
        
        if has_analysis:
            analysis_dir = base_dir / 'ai_analysis'
            analysis_dir.mkdir(parents=True, exist_ok=True)
            analysis_path = str(analysis_dir / f"{safe_identifier}_analysis_{timestamp}.json")
        else:
            analysis_path = None
    
    return result_path, analysis_path


async def run_scraper_command(
    config_path: str,
    command_func: Callable[[XScraper], Awaitable[None]],
    error_message: str = "Command failed"
) -> None:
    scraper = XScraper(config_path)
    
    try:
        if not await scraper.login():
            click.echo("Failed to login to Twitter", err=True)
            return
        
        await command_func(scraper)
        
    except AuthenticationError as e:
        click.echo(f"Authentication error: {e}", err=True)
        click.echo("Tip: Check your credentials in config.ini or refresh your session", err=True)
    except RateLimitError as e:
        wait_time = e.retry_after or 900
        click.echo(f"Rate limit reached: {e}", err=True)
        click.echo(f"Tip: Wait {wait_time}s or use a different account/proxy", err=True)
    except BotDetectionError as e:
        click.echo(f"Bot detection triggered: {e}", err=True)
        click.echo("Tip: Increase delays in config.ini or use a residential proxy", err=True)
    except NetworkError as e:
        click.echo(f"Network error: {e}", err=True)
        click.echo("Tip: Check your internet connection or proxy settings", err=True)
    except ScrapingError as e:
        click.echo(f"Scraping error: {e}", err=True)
    except XScraperError as e:
        click.echo(f"{error_message}: {e}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        click.echo(f"{error_message}: {str(e)}", err=True)
    finally:
        await scraper.cleanup()

