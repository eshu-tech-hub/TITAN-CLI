import typer

from titan.core.config import get_settings
from titan.core.logger import logger

app = typer.Typer(
    name="titan",
    help="TITAN CLI - Institutional Trading Intelligence System",
)

settings = get_settings()


@app.command("version")
def version():
    """Display TITAN version information."""
    logger.info("Version command executed")

    print("=" * 50)
    print(settings.app_name)
    print("Institutional Trading Intelligence System")
    print(f"Version : {settings.app_version}")
    print(f"Status  : {settings.environment}")
    print("=" * 50)


@app.command("status")
def status():
    """Display TITAN status."""
    logger.info("Status command executed")
    print("Status : Development")