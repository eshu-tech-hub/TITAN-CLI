"""
Canonical certification scenarios for the Broker Certification Framework.

Categories include:
Authentication, Session, Market Data, Orders, Positions, Holdings,
Funds, Margin, Recovery, Runtime, Performance, Compliance.
"""

from titan.brokers.certification.models import (
    BrokerCertificationScenario,
    CertificationSeverity,
)

# Authentication Scenarios
AUTH_LOGIN = BrokerCertificationScenario(
    scenario_id="AUTH_LOGIN",
    name="Valid Login",
    description="Attempt login with valid credentials.",
    category="Authentication",
    severity=CertificationSeverity.CRITICAL,
    expected_behavior="Broker successfully authenticates and returns valid session tokens.",
    pass_criteria=("Status code 200", "Token present in response"),
)

AUTH_INVALID_CREDENTIALS = BrokerCertificationScenario(
    scenario_id="AUTH_INVALID_CREDENTIALS",
    name="Invalid Credentials",
    description="Attempt login with invalid credentials.",
    category="Authentication",
    severity=CertificationSeverity.HIGH,
    expected_behavior="Broker rejects authentication with appropriate error code.",
    pass_criteria=("Status code 401 or 403", "No token in response"),
)

# Session Scenarios
SESSION_REFRESH = BrokerCertificationScenario(
    scenario_id="SESSION_REFRESH",
    name="Session Refresh",
    description="Refresh an active session token.",
    category="Session",
    severity=CertificationSeverity.HIGH,
    expected_behavior="Broker provides a new valid session token.",
    pass_criteria=("Status code 200", "New token differs from old token"),
)

SESSION_EXPIRED = BrokerCertificationScenario(
    scenario_id="SESSION_EXPIRED",
    name="Expired Session Handling",
    description="Attempt API call with expired session token.",
    category="Session",
    severity=CertificationSeverity.HIGH,
    expected_behavior="Broker rejects request due to expiration.",
    pass_criteria=("Status code 401", "Error message indicates expiration"),
)

SESSION_LOGOUT = BrokerCertificationScenario(
    scenario_id="SESSION_LOGOUT",
    name="Graceful Logout",
    description="Explicitly terminate the session.",
    category="Session",
    severity=CertificationSeverity.MEDIUM,
    expected_behavior="Broker invalidates the session.",
    pass_criteria=("Status code 200", "Subsequent calls with token fail"),
)

# Market Data Scenarios
MARKET_DATA_LTP = BrokerCertificationScenario(
    scenario_id="MARKET_DATA_LTP",
    name="Last Traded Price",
    description="Fetch the latest price for a known instrument.",
    category="Market Data",
    severity=CertificationSeverity.CRITICAL,
    expected_behavior="Broker returns current market price.",
    pass_criteria=("Valid numeric price", "Timestamp included"),
)

# Orders Scenarios
ORDER_MARKET_BUY = BrokerCertificationScenario(
    scenario_id="ORDER_MARKET_BUY",
    name="Market Order (Buy)",
    description="Place a market buy order for a valid instrument.",
    category="Orders",
    severity=CertificationSeverity.CRITICAL,
    expected_behavior="Broker accepts order and returns order ID.",
    pass_criteria=("Order ID present", "Order status is OPEN or COMPLETED"),
)

ORDER_LIMIT_SELL = BrokerCertificationScenario(
    scenario_id="ORDER_LIMIT_SELL",
    name="Limit Order (Sell)",
    description="Place a limit sell order for a valid instrument.",
    category="Orders",
    severity=CertificationSeverity.CRITICAL,
    expected_behavior="Broker accepts order and returns order ID.",
    pass_criteria=("Order ID present", "Order status is OPEN or PENDING"),
)

ORDER_MODIFY = BrokerCertificationScenario(
    scenario_id="ORDER_MODIFY",
    name="Modify Open Order",
    description="Modify the price or quantity of an open limit order.",
    category="Orders",
    severity=CertificationSeverity.HIGH,
    expected_behavior="Broker successfully updates the order details.",
    pass_criteria=("Modification successful response", "Order details reflect changes"),
)

ORDER_CANCEL = BrokerCertificationScenario(
    scenario_id="ORDER_CANCEL",
    name="Cancel Open Order",
    description="Cancel an existing open order.",
    category="Orders",
    severity=CertificationSeverity.CRITICAL,
    expected_behavior="Broker successfully cancels the order.",
    pass_criteria=("Cancellation successful response", "Order status is CANCELLED"),
)

# Holdings & Positions Scenarios
POSITIONS_FETCH = BrokerCertificationScenario(
    scenario_id="POSITIONS_FETCH",
    name="Fetch Open Positions",
    description="Retrieve all current open positions.",
    category="Positions",
    severity=CertificationSeverity.HIGH,
    expected_behavior="Broker returns list of positions.",
    pass_criteria=("Response is list", "Position models match expected schema"),
)

HOLDINGS_FETCH = BrokerCertificationScenario(
    scenario_id="HOLDINGS_FETCH",
    name="Fetch Holdings",
    description="Retrieve all current portfolio holdings.",
    category="Holdings",
    severity=CertificationSeverity.HIGH,
    expected_behavior="Broker returns list of holdings.",
    pass_criteria=("Response is list", "Holding models match expected schema"),
)

# Funds & Margin Scenarios
FUNDS_FETCH = BrokerCertificationScenario(
    scenario_id="FUNDS_FETCH",
    name="Fetch Funds",
    description="Retrieve account balance and fund details.",
    category="Funds",
    severity=CertificationSeverity.CRITICAL,
    expected_behavior="Broker returns fund summary.",
    pass_criteria=("Available margin is numeric", "Used margin is numeric"),
)

MARGIN_CALCULATE = BrokerCertificationScenario(
    scenario_id="MARGIN_CALCULATE",
    name="Calculate Margin Requirement",
    description="Calculate required margin for an intended order.",
    category="Margin",
    severity=CertificationSeverity.MEDIUM,
    expected_behavior="Broker returns required margin amount.",
    pass_criteria=("Margin requirement is numeric",),
)

# Recovery Scenarios
RECOVERY_DISCONNECT = BrokerCertificationScenario(
    scenario_id="RECOVERY_DISCONNECT",
    name="Network Disconnect Handling",
    description="Simulate network disconnect during an active operation.",
    category="Recovery",
    severity=CertificationSeverity.HIGH,
    expected_behavior="Broker SDK throws appropriate network exception.",
    pass_criteria=("Network exception raised",),
)

RECOVERY_RETRY = BrokerCertificationScenario(
    scenario_id="RECOVERY_RETRY",
    name="Automatic Retry Logic",
    description="Test SDK's ability to retry on transient failures.",
    category="Recovery",
    severity=CertificationSeverity.MEDIUM,
    expected_behavior="SDK transparently retries and eventually succeeds or fails gracefully.",
    pass_criteria=("Retry count observed",),
)

# Runtime Scenarios
RUNTIME_HEARTBEAT = BrokerCertificationScenario(
    scenario_id="RUNTIME_HEARTBEAT",
    name="Connection Heartbeat",
    description="Maintain connection via periodic heartbeats.",
    category="Runtime",
    severity=CertificationSeverity.MEDIUM,
    expected_behavior="Connection remains active over extended period.",
    pass_criteria=("No silent drops", "Heartbeat acknowledged"),
)

# Performance Scenarios
PERFORMANCE_LATENCY = BrokerCertificationScenario(
    scenario_id="PERFORMANCE_LATENCY",
    name="Order Placement Latency",
    description="Measure time taken to place an order and receive acknowledgment.",
    category="Performance",
    severity=CertificationSeverity.MEDIUM,
    expected_behavior="Order placement should complete within acceptable latency limits.",
    pass_criteria=("Latency < 500ms",),
)

# Compliance Scenarios
COMPLIANCE_RATE_LIMITS = BrokerCertificationScenario(
    scenario_id="COMPLIANCE_RATE_LIMITS",
    name="Rate Limit Compliance",
    description="Ensure SDK correctly handles rate limit headers/errors without violating terms.",
    category="Compliance",
    severity=CertificationSeverity.HIGH,
    expected_behavior="SDK backs off when rate limits are approached.",
    pass_criteria=(
        "No ban/block due to spamming",
        "Rate limit errors handled gracefully",
    ),
)

# Master list of all scenarios
ALL_SCENARIOS = (
    AUTH_LOGIN,
    AUTH_INVALID_CREDENTIALS,
    SESSION_REFRESH,
    SESSION_EXPIRED,
    SESSION_LOGOUT,
    MARKET_DATA_LTP,
    ORDER_MARKET_BUY,
    ORDER_LIMIT_SELL,
    ORDER_MODIFY,
    ORDER_CANCEL,
    POSITIONS_FETCH,
    HOLDINGS_FETCH,
    FUNDS_FETCH,
    MARGIN_CALCULATE,
    RECOVERY_DISCONNECT,
    RECOVERY_RETRY,
    RUNTIME_HEARTBEAT,
    PERFORMANCE_LATENCY,
    COMPLIANCE_RATE_LIMITS,
)
