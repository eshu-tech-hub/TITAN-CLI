from titan.core.readiness import ProductionReadinessReview


def test_production_readiness_report():
    report = ProductionReadinessReview.evaluate()

    assert report.is_ready is True
    assert report.overall_score == "Good"
    assert len(report.known_risks) > 0

    data = report.to_dict()
    assert data["architecture_score"] == "Excellent"
    assert data["observability_score"] == "Acceptable"
