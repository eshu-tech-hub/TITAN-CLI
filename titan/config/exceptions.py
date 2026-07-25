class ConfigError(Exception):
    """Base exception for configuration errors."""


class ProfileNotFoundError(ConfigError):
    """Requested profile does not exist."""


class ConfigValidationError(ConfigError):
    """Configuration failed validation."""


class ConfigLoadError(ConfigError):
    """Configuration could not be loaded from source."""


class SecretNotFoundError(ConfigError):
    """Required secret is not available."""


class ConfigMergeError(ConfigError):
    """Configuration sources could not be merged."""
