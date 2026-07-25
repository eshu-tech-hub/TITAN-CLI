import os

from titan.core.exceptions import ConfigurationError


class Settings:
    """
    Application configuration.
    """

    @property
    def angel_api_key(self) -> str:
        value = os.getenv("ANGEL_API_KEY")

        if not value:
            raise ConfigurationError("ANGEL_API_KEY is not configured.")

        return value

    @property
    def angel_client_id(self) -> str:
        value = os.getenv("ANGEL_CLIENT_ID")

        if not value:
            raise ConfigurationError("ANGEL_CLIENT_ID is not configured.")

        return value

    @property
    def angel_pin(self) -> str:
        value = os.getenv("ANGEL_PIN")

        if not value:
            raise ConfigurationError("ANGEL_PIN is not configured.")

        return value

    @property
    def angel_totp_secret(self) -> str:
        value = os.getenv("ANGEL_TOTP_SECRET")

        if not value:
            raise ConfigurationError("ANGEL_TOTP_SECRET is not configured.")

        return value


settings = Settings()
