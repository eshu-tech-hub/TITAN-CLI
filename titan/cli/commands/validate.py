import typer
from rich.console import Console

from titan.validation.runner import ValidationOrchestrator

app = typer.Typer(help="Run TITAN operational validation and burn-in.")
console = Console()


@app.command("burn-in")
def burn_in(hours: float = 8.0):
    """Run accelerated burn-in validation."""
    console.print(f"Starting burn-in simulation for {hours} hours...")
    orchestrator = ValidationOrchestrator()
    report = orchestrator.run_burn_in(hours)
    console.print(report)


@app.command("stress")
def stress():
    """Run subsystem stress tests."""
    console.print("Starting stress validation...")
    orchestrator = ValidationOrchestrator()
    report = orchestrator.run_stress()
    console.print(report)


@app.command("performance")
def performance():
    """Profile runtime performance metrics."""
    console.print("Starting performance profiling...")
    orchestrator = ValidationOrchestrator()
    report = orchestrator.run_performance()
    console.print(report)


@app.command("reliability")
def reliability():
    """Calculate and display reliability metrics."""
    console.print("Calculating reliability metrics...")
    orchestrator = ValidationOrchestrator()
    report = orchestrator.run_reliability()
    console.print(report)


@app.command("report")
def report():
    """Generate the comprehensive ValidationReport."""
    console.print("Generating full validation report...")
    orchestrator = ValidationOrchestrator()
    rep = orchestrator.generate_full_report()
    console.print(f"Validation Status: [bold green]{rep.overall_status}[/bold green]")
