from typing import Any

from titan.brokers.exceptions import (
    AuthenticationError,
    BrokerError,
    ConnectionError,
    MarketDataError,
    OrderError,
)

_ERROR_MAP: dict[str, type[BrokerError]] = {
    "AB1010": AuthenticationError,
    "AB1011": AuthenticationError,
    "AB1012": AuthenticationError,
    "AB2000": OrderError,
    "AB2001": OrderError,
    "AB2002": OrderError,
    "AB3000": MarketDataError,
    "AB4000": ConnectionError,
}

_DEFAULT_MESSAGE = "An unexpected Angel One SmartAPI error occurred."


def translate_error(exc: Any) -> BrokerError:
    """Translate a SmartAPI exception into a TITAN broker exception.

    Args:
        exc: The exception raised by the SmartAPI SDK.

    Returns:
        An instance of a TITAN broker exception (AuthenticationError,
        ConnectionError, OrderError, MarketDataError, or BrokerError).
    """
    error_code: str = ""
    error_message: str = _DEFAULT_MESSAGE

    if hasattr(exc, "code") and exc.code:
        error_code = str(exc.code)
    if hasattr(exc, "message") and exc.message:
        error_message = str(exc.message)
    elif exc.args:
        error_message = str(exc.args[0])

    error_cls = _ERROR_MAP.get(error_code, BrokerError)
    msg = f"[{error_code}] {error_message}" if error_code else error_message
    return error_cls(msg)
