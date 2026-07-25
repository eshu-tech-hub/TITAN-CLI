from titan.validation.fault_injection import FaultScenario, FaultInjectionPoint


def test_fault_scenario_enum_contains_expected_values():
    assert FaultScenario.BrokerDisconnect is not None
    assert FaultScenario.HeartbeatTimeout is not None


def test_fault_injection_point_initialization():
    point = FaultInjectionPoint(
        scenario=FaultScenario.BrokerDisconnect,
        target_component="BrokerAdapter",
        trigger_condition=lambda x: True,
        fault_action=lambda x: None,
    )
    assert point.target_component == "BrokerAdapter"
    assert point.scenario == FaultScenario.BrokerDisconnect
