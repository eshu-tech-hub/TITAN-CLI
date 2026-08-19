from datetime import datetime

from titan.validation.reports import BurnInReport, StressReport


def test_burn_in_report_markdown_serialization():
    report = BurnInReport(
        timestamp=datetime(2026, 1, 1),
        duration_hours=8.0,
        faults_injected=5,
        recoveries_successful=5,
        failures_observed=[],
        final_assessment="Pass",
    )
    md = report.to_markdown()
    assert "# TITAN Burn-In Report" in md
    assert "2026-01-01T00:00:00" in md


def test_stress_report_markdown_serialization():
    report = StressReport(
        timestamp=datetime(2026, 1, 1),
        events_processed=1000,
        peak_throughput_eps=100.0,
        bottlenecks_detected=[],
        final_assessment="Pass",
    )
    md = report.to_markdown()
    assert "# TITAN Stress Test Report" in md
