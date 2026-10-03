"""Typed failures with fixed messages; never include identities or provider payloads."""

from enum import StrEnum


class Dota2ForgeError(Exception):
    """Base for expected application failures."""


class ValidationError(Dota2ForgeError, ValueError):
    """An input or normalized value violates a contract."""


class InvalidSteamIdError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Expected a supported Dota account ID or public individual SteamID64")


class InvalidIdentityError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Invalid platform identity")


class BindingNotFoundError(Dota2ForgeError):
    def __init__(self) -> None:
        super().__init__("No account is bound to this identity")


class BindingConflictError(Dota2ForgeError):
    def __init__(self) -> None:
        super().__init__("An account is already bound; replacement must be explicit")


class RepositoryError(Dota2ForgeError):
    def __init__(self) -> None:
        super().__init__("Binding storage is unavailable, incompatible, or contains invalid data")


class CacheError(Dota2ForgeError):
    def __init__(self) -> None:
        super().__init__("Provider cache is unavailable or contains invalid data")


class SubscriptionRepositoryError(Dota2ForgeError):
    def __init__(self) -> None:
        super().__init__("Subscription storage is unavailable, incompatible, or invalid")


class SubscriptionCapacityError(Dota2ForgeError):
    def __init__(self) -> None:
        super().__init__("Subscription or pending-event capacity has been reached")


class DataSource(StrEnum):
    FIXTURE = "fixture"
    STRATZ = "stratz"
    OPENDOTA = "opendota"
    STEAM = "steam"


class ProviderErrorCode(StrEnum):
    NOT_FOUND = "not_found"
    PRIVATE = "private"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    AUTHENTICATION = "authentication"
    INVALID_RESPONSE = "invalid_response"


class ProviderError(Dota2ForgeError):
    def __init__(
        self,
        code: ProviderErrorCode,
        source: DataSource,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        if not isinstance(code, ProviderErrorCode) or not isinstance(source, DataSource):
            raise ValidationError("Invalid provider error classification")
        if retry_after_seconds is not None and (
            code != ProviderErrorCode.RATE_LIMITED
            or type(retry_after_seconds) is not int
            or retry_after_seconds < 0
        ):
            raise ValidationError("Invalid retry delay")
        self.code = code
        self.source = source
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Provider {source.value}: {code.value}")
