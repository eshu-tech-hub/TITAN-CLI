"""
Tests for Broker Certification Reports.
"""

from titan.brokers.certification.models import (
    BrokerCapability,
    BrokerCertificationScenario,
    BrokerCertificationResult,
    CertificationStatus,
    CertificationSeverity,
)
from titan.brokers.certification.report import (
    BrokerCapabilityMatrixBuilder,
    CertificationReportBuilder,
)


def test_capability_matrix_builder():
    builder = BrokerCapabilityMatrixBuilder(broker_id="BROKER_A")
    cap1 = BrokerCapability("CAP_1", "Cap 1", "Desc", True)
    cap2 = BrokerCapability("CAP_2", "Cap 2", "Desc", False)

    matrix = builder.add_capability(cap1).add_capability(cap2).build()

    assert matrix.broker_id == "BROKER_A"
    assert len(matrix.capabilities) == 2
    assert matrix.capabilities[0].capability_id == "CAP_1"


def test_report_builder_summary_calculation():
    builder = CertificationReportBuilder(report_id="RPT_1", broker_id="BROKER_A")

    # Needs a matrix
    matrix_builder = BrokerCapabilityMatrixBuilder(broker_id="BROKER_A")
    builder.set_capability_matrix(matrix_builder.build())

    scenario = BrokerCertificationScenario(
        scenario_id="S_1",
        name="S 1",
        description="D",
        category="C",
        severity=CertificationSeverity.CRITICAL,
        expected_behavior="E",
    )

    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)

    builder.add_scenario_result(
        BrokerCertificationResult(
            scenario=scenario,
            status=CertificationStatus.PASS,
            execution_time_ms=10.0,
            timestamp=now,
        )
    )

    builder.add_scenario_result(
        BrokerCertificationResult(
            scenario=scenario,
            status=CertificationStatus.FAIL,
            execution_time_ms=20.0,
            timestamp=now,
        )
    )

    report = builder.build()

    assert report.summary.total_scenarios == 2
    assert report.summary.passed_scenarios == 1
    assert report.summary.failed_scenarios == 1
    assert report.summary.critical_failures == 1
    assert report.summary.status == CertificationStatus.FAIL
