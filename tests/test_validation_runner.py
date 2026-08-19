from titan.validation.reports import BurnInReport, ValidationReport
from titan.validation.runner import ValidationOrchestrator


def test_runner_burn_in_report_generation():
    orchestrator = ValidationOrchestrator()
    report = orchestrator.run_burn_in(4.0)
    assert isinstance(report, BurnInReport)
    assert report.duration_hours == 4.0
    assert report.faults_injected == 10


def test_runner_full_report_generation():
    orchestrator = ValidationOrchestrator()
    report = orchestrator.generate_full_report()
    assert isinstance(report, ValidationReport)
    assert report.overall_status == "CERTIFIED"
    assert report.burn_in is not None
    assert report.stress is not None
