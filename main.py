import click
from rich.console import Console

from cli import user, search, search_historical, interactive, refresh_session


console = Console()


@click.group()
@click.option('--config', '-c', default='config.ini', help='Configuration file path')
@click.pass_context
def cli(ctx: click.Context, config: str) -> None:
    ctx.ensure_object(dict)
    ctx.obj['config'] = config


cli.add_command(user)
cli.add_command(search)
cli.add_command(search_historical)
cli.add_command(interactive)
cli.add_command(refresh_session)


def main() -> None:
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")


if __name__ == "__main__":
    main()
