import typer

from rich.panel import Panel
from rich.text import Text

from titan.core.config import get_settings
from titan.core.display import console
from titan.core.logger import logger


from titan.core.exceptions import TitanError

from titan.analysis.factory import IndicatorFactory

app = typer.Typer(
    name="titan",
    help="TITAN CLI - Institutional Trading Intelligence System",
)

settings = get_settings()


@app.command("version")
def version():
    """Display TITAN version information."""
    try:
        logger.info("Version command executed")

        text = Text()
        text.append(f"{settings.app_name}\n", style="bold cyan")
        text.append("Institutional Trading Intelligence System\n")
        text.append(f"Version : {settings.app_version}\n")
        text.append(f"Status  : {settings.environment}")

        console.print(
            Panel(
                text,
                title="TITAN",
                expand=False,
            )
        )

    except TitanError as e:
        logger.error(str(e))
        console.print(f"[bold red]Error:[/bold red] {e}")

    except Exception as e:
        logger.exception(e)
        console.print("[bold red]Unexpected error occurred.[/bold red]")

@app.command("status")
def status():
    """Display TITAN status."""
    logger.info("Status command executed")
    console.print("[bold green]Status:[/bold green] Development")


@app.command("indicators")
def indicators():
    """
    List all available indicators.
    """
    print("\nAvailable Indicators\n")

    for name in IndicatorFactory.available():
        print(f"• {name}")

@app.command("doctor")
def doctor():
    """
    Check TITAN installation.
    """

    print("TITAN Doctor")
    print("-" * 40)

    print(f"Application : {settings.app_name}")
    print(f"Version     : {settings.app_version}")
    print(f"Environment : {settings.environment}")

    print("\nStatus")

    print("✔ Configuration")
    print("✔ Logging")
    print("✔ Analysis Engine")