import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from src import XScraper
from src.ai_analyzer import AnalysisType


console = Console()


class XScraperCLI:
    
    def __init__(self) -> None:
        self.scraper: Optional[XScraper] = None
        self.config_path: str = "config.ini"
    
    async def initialize_scraper(self) -> bool:
        try:
            with console.status("[bold green]Initializing X-Scraper..."):
                self.scraper = XScraper(self.config_path)
            
            console.print("[green]✓[/green] X-Scraper initialized successfully")
            return True
            
        except FileNotFoundError:
            console.print("[red]✗[/red] Configuration file not found. Please ensure config.ini exists.")
            return False
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to initialize scraper: {str(e)}")
            return False
    
    async def login_to_twitter(self) -> bool:
        if not self.scraper:
            console.print("[red]✗[/red] Scraper not initialized")
            return False
        
        try:
            with console.status("[bold blue]Logging in to Twitter..."):
                success = await self.scraper.login()
            
            if success:
                console.print("[green]✓[/green] Successfully logged in to Twitter")
                return True
            else:
                console.print("[red]✗[/red] Failed to login to Twitter. Check your credentials.")
                return False
                
        except Exception as e:
            console.print(f"[red]✗[/red] Login failed: {str(e)}")
            return False
    
    def display_welcome(self) -> None:
        welcome_text = """
[bold blue]X-Scraper[/bold blue] - Advanced Twitter Scraper
        
Features:
• [green]Browser Automation[/green] - Deep historical scraping
• [green]AI Analysis[/green] - Powered by OpenAI/Anthropic  
• [green]JSON Export[/green] - Clean structured data format
• [green]Advanced Filtering[/green] - Customizable content filters
• [green]Rate Limiting[/green] - Smart request management
        """
        
        console.print(Panel(welcome_text, title="Welcome", border_style="blue"))
    
    def display_menu(self) -> None:
        menu_table = Table(title="Main Menu", show_header=True, header_style="bold magenta")
        menu_table.add_column("Option", style="cyan", width=8)
        menu_table.add_column("Description", style="white")
        
        menu_table.add_row("1", "Search tweets by query")
        menu_table.add_row("2", "Scrape user tweets")
        menu_table.add_row("3", "View session statistics")
        menu_table.add_row("4", "Configuration settings")
        menu_table.add_row("5", "Exit")
        
        console.print(menu_table)
    
    async def search_tweets_interactive(self) -> None:
        console.print("\n[bold cyan]Tweet Search[/bold cyan]")
        
        if not self.scraper:
            console.print("[red]✗[/red] Scraper not initialized")
            return
        
        query = Prompt.ask("Enter search query")
        if not query:
            console.print("[red]Search query cannot be empty[/red]")
            return
        
        count = Prompt.ask("Number of tweets to retrieve", default="50")
        try:
            count = int(count)
        except ValueError:
            count = 50
        
        result_type = Prompt.ask(
            "Result type", 
            choices=["Latest", "Top", "Media"], 
            default="Latest"
        )
        
        analyze = Confirm.ask("Perform AI analysis?", default=True)
        
        analysis_types = []
        if analyze:
            console.print("\nAvailable analysis types:")
            available_types = [t.value for t in AnalysisType]
            for i, analysis_type in enumerate(available_types, 1):
                console.print(f"{i}. {analysis_type}")
            
            selected = Prompt.ask(
                "Select analysis types (comma-separated numbers or 'all')", 
                default="all"
            )
            
            if selected.lower() == "all":
                analysis_types = available_types
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selected.split(",")]
                    analysis_types = [available_types[i] for i in indices if 0 <= i < len(available_types)]
                except (ValueError, IndexError):
                    analysis_types = ["sentiment", "topics", "summary"]
        
        try:
            with console.status("[bold cyan]Searching tweets for '{query}'..."):
                
                result = await self.scraper.search_tweets(
                    query=query,
                    count=count,
                    result_type=result_type,
                    analyze=analyze,
                    analysis_types=analysis_types
                )
            
            self.display_search_results(result)
            
        except Exception as e:
            console.print(f"[red]✗[/red] Search failed: {str(e)}")
    
    async def scrape_user_tweets_interactive(self) -> None:
        console.print("\n[bold cyan]User Tweet Scraping[/bold cyan]")
        
        if not self.scraper:
            console.print("[red]✗[/red] Scraper not initialized")
            return
        
        username = Prompt.ask("Enter username (without @)")
        if not username:
            console.print("[red]Username cannot be empty[/red]")
            return
        
        unlimited = True
        browser_mode = True
        count = None
        resume = False
        
        from src.checkpoint_manager import CheckpointManager
        checkpoint_mgr = CheckpointManager()
        if checkpoint_mgr.has_checkpoint(username):
            checkpoint = checkpoint_mgr.load_checkpoint(username)
            if checkpoint:
                console.print(f"\n[yellow]Found existing checkpoint:[/yellow]")
                console.print(f"   Total tweets: {checkpoint.get('total_tweets', 0)}")
                console.print(f"   Last scraped: {checkpoint.get('oldest_tweet_date', 'Unknown')}")
                console.print(f"   Sessions: {checkpoint.get('session_count', 1)}")
                resume = Confirm.ask("Resume from this checkpoint?", default=True)
        
        console.print("[yellow]Will open Chrome browser and collect complete historical data[/yellow]")
        
        max_tweets_per_session = self.scraper.config_manager.get_scraping_settings()['max_tweets_per_session']
        console.print(f"[green]✓[/green] Session limit: {max_tweets_per_session} tweets per session")
        console.print(f"[dim]   (Use resume to continue in next session)[/dim]")
        
        analyze = Confirm.ask("Perform AI analysis?", default=True)
        
        analysis_types = []
        if analyze:
            console.print("\nAvailable analysis types:")
            available_types = [t.value for t in AnalysisType]
            for i, analysis_type in enumerate(available_types, 1):
                console.print(f"{i}. {analysis_type}")
            
            selected = Prompt.ask(
                "Select analysis types (comma-separated numbers or 'all')", 
                default="all"
            )
            
            if selected.lower() == "all":
                analysis_types = available_types
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selected.split(",")]
                    analysis_types = [available_types[i] for i in indices if 0 <= i < len(available_types)]
                except (ValueError, IndexError):
                    analysis_types = ["sentiment", "topics", "summary"]
        
        try:
            with console.status("[bold cyan]Scraping tweets from @{username}..."):
                
                result = await self.scraper.scrape_user_tweets(
                    username=username,
                    count=count,
                    analyze=analyze,
                    analysis_types=analysis_types,
                    unlimited_history=unlimited,
                    browser_mode=browser_mode,
                    resume=resume,
                    max_tweets_per_session=max_tweets_per_session
                )
            
            self.display_user_results(result)
            
        except Exception as e:
            console.print(f"[red]✗[/red] Scraping failed: {str(e)}")
    
    def display_search_results(self, result: Dict[str, Any]) -> None:
        console.print(f"\n[bold green]Search Results[/bold green]")
        
        summary_table = Table(title="Summary", show_header=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Query", result.get('query', 'N/A'))
        summary_table.add_row("Total Tweets", str(result.get('tweet_count', 0)))
        summary_table.add_row("Filtered Tweets", str(result.get('filtered_tweet_count', 0)))
        
        console.print(summary_table)
        
        tweets = result.get('tweets', [])
        if tweets:
            console.print(f"\n[bold]Sample Tweets (showing first 5):[/bold]")
            for i, tweet in enumerate(tweets[:5], 1):
                user = tweet.get('user', {})
                metrics = tweet.get('metrics', {})
                
                tweet_panel = Panel(
                    f"[bold]@{user.get('username', 'unknown')}[/bold] ({user.get('display_name', 'Unknown')})\n"
                    f"{tweet.get('text', '')}\n\n"
                    f"[dim]Fav: {metrics.get('favorite_count', 0)} | "
                    f"Retweet: {metrics.get('retweet_count', 0)} | "
                    f"Reply: {metrics.get('reply_count', 0)}[/dim]",
                    title=f"Tweet {i}",
                    border_style="green"
                )
                console.print(tweet_panel)
        
        if result.get('analysis'):
            self.display_analysis_results(result['analysis'])
    
    def display_user_results(self, result: Dict[str, Any]) -> None:
        console.print(f"\n[bold green]User Scraping Results[/bold green]")
        
        summary_table = Table(title="Summary", show_header=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Username", f"@{result.get('username', 'N/A')}")
        summary_table.add_row("Total Tweets", str(result.get('tweet_count', 0)))
        summary_table.add_row("Filtered Tweets", str(result.get('filtered_tweet_count', 0)))
        
        console.print(summary_table)
        
        tweets = result.get('tweets', [])
        if tweets:
            console.print(f"\n[bold]Recent Tweets (showing first 5):[/bold]")
            for i, tweet in enumerate(tweets[:5], 1):
                metrics = tweet.get('metrics', {})
                
                tweet_panel = Panel(
                    f"{tweet.get('text', '')}\n\n"
                    f"[dim]Fav: {metrics.get('favorite_count', 0)} | "
                    f"Retweet: {metrics.get('retweet_count', 0)} | "
                    f"Reply: {metrics.get('reply_count', 0)} | "
                    f"Date: {tweet.get('created_at', 'Unknown')}[/dim]",
                    title=f"Tweet {i}",
                    border_style="blue"
                )
                console.print(tweet_panel)
        
        if result.get('analysis'):
            self.display_analysis_results(result['analysis'])
    
    def display_analysis_results(self, analysis: Dict[str, Any]) -> None:
        console.print(f"\n[bold magenta]AI Analysis Results[/bold magenta]")
        
        analyses = analysis.get('analyses', {})
        
        for analysis_type, analysis_data in analyses.items():
            if isinstance(analysis_data, dict) and 'error' not in analysis_data:
                console.print(f"\n[bold cyan]{analysis_type.title()} Analysis:[/bold cyan]")
                
                if analysis_type == 'sentiment':
                    self._display_sentiment_analysis(analysis_data)
                elif analysis_type == 'topics':
                    self._display_topics_analysis(analysis_data)
                elif analysis_type == 'summary':
                    self._display_summary_analysis(analysis_data)
                else:
                    if 'analysis' in analysis_data:
                        console.print(analysis_data['analysis'])
                    else:
                        console.print(str(analysis_data))
            else:
                console.print(f"[red]{analysis_type} analysis failed: {analysis_data.get('error', 'Unknown error')}[/red]")
    
    def _display_sentiment_analysis(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict) and 'analysis' in data:
            console.print(data['analysis'])
        else:
            console.print(str(data))
    
    def _display_topics_analysis(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict) and 'analysis' in data:
            console.print(data['analysis'])
        else:
            console.print(str(data))
    
    def _display_summary_analysis(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict) and 'analysis' in data:
            console.print(data['analysis'])
        else:
            console.print(str(data))
    
    
    def display_session_stats(self) -> None:
        console.print("\n[bold cyan]Session Statistics[/bold cyan]")
        
        if not self.scraper:
            console.print("[red]Scraper not initialized[/red]")
            return
        
        stats = self.scraper.get_session_stats()
        
        main_table = Table(title="Session Overview", show_header=False)
        main_table.add_column("Metric", style="cyan")
        main_table.add_column("Value", style="white")
        
        main_table.add_row("Tweets Scraped", str(stats.get('tweets_scraped', 0)))
        main_table.add_row("Analyses Performed", str(stats.get('analyses_performed', 0)))
        main_table.add_row("Errors Encountered", str(stats.get('errors_encountered', 0)))
        
        if 'duration' in stats:
            duration = stats['duration']
            main_table.add_row("Session Duration", f"{duration:.1f} seconds")
        
        console.print(main_table)
        
        if 'twitter_stats' in stats:
            twitter_stats = stats['twitter_stats']
            console.print(f"\n[bold]Twitter Client Stats:[/bold]")
            console.print(f"Requests Made: {twitter_stats.get('requests_made', 0)}")
            console.print(f"Requests/Minute: {twitter_stats.get('requests_per_minute', 0):.1f}")
        
    def display_config_settings(self) -> None:
        console.print("\n[bold cyan]Configuration Settings[/bold cyan]")
        
        if not self.scraper:
            console.print("[red]Scraper not initialized[/red]")
            return
        
        try:
            scraping_settings = self.scraper.config_manager.get_scraping_settings()
            ai_settings = self.scraper.config_manager.get_ai_settings()
            
            scraping_table = Table(title="Scraping Settings", show_header=False)
            scraping_table.add_column("Setting", style="cyan")
            scraping_table.add_column("Value", style="white")
            
            scraping_table.add_row("Default Tweet Count", str(scraping_settings.get('default_tweet_count', 50)))
            scraping_table.add_row("Max Tweet Count", str(scraping_settings.get('max_tweet_count', 1000)))
            scraping_table.add_row("Output Format", scraping_settings.get('output_format', 'json'))
            scraping_table.add_row("Save to File", str(scraping_settings.get('save_to_file', True)))
            
            console.print(scraping_table)
            
            ai_table = Table(title="AI Settings", show_header=False)
            ai_table.add_column("Setting", style="cyan")
            ai_table.add_column("Value", style="white")
            
            ai_table.add_row("Provider", ai_settings.get('provider', 'Not configured'))
            ai_table.add_row("Model", ai_settings.get('model', 'Not configured'))
            ai_table.add_row("Max Tokens", str(ai_settings.get('max_tokens', 1000)))
            
            console.print(ai_table)
            
        except Exception as e:
            console.print(f"[red]Error loading configuration: {str(e)}[/red]")
    
    async def run_interactive_mode(self) -> None:
        self.display_welcome()
        
        if not await self.initialize_scraper():
            return
        
        while True:
            try:
                console.print("\n")
                self.display_menu()
                
                choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])
                
                if choice == "1":
                    await self.search_tweets_interactive()
                elif choice == "2":
                    await self.scrape_user_tweets_interactive()
                elif choice == "3":
                    self.display_session_stats()
                elif choice == "4":
                    self.display_config_settings()
                elif choice == "5":
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                
                if choice in ["1", "2"]:
                    if not Confirm.ask("\nContinue with another operation?", default=True):
                        break
                        
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled by user[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Unexpected error: {str(e)}[/red]")
        
        if self.scraper:
            await self.scraper.cleanup()


@click.command()
@click.pass_context
def interactive(ctx: click.Context) -> None:
    async def run_interactive() -> None:
        cli_app = XScraperCLI()
        cli_app.config_path = ctx.obj['config']
        await cli_app.run_interactive_mode()
    
    asyncio.run(run_interactive())

