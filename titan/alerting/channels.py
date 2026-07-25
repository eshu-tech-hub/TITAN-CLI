from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from threading import Lock

from titan.alerting.exceptions import AlertingChannelError, AlertingDispatchError
from titan.alerting.models import (
    Alert,
    ChannelConfig,
    ChannelType,
    NotificationAttempt,
    NotificationResult,
    level_rank,
)


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, alert: Alert) -> NotificationResult: ...

    @property
    @abstractmethod
    def channel_type(self) -> ChannelType: ...


@dataclass(slots=True)
class ConsoleChannel(NotificationChannel):
    _channel_type: ChannelType = ChannelType.CONSOLE

    @property
    def channel_type(self) -> ChannelType:
        return self._channel_type

    def send(self, alert: Alert) -> NotificationResult:
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        print(
            f"[{timestamp}] [{alert.level.value.upper()}] "
            f"[{alert.source.value}] {alert.title}: {alert.message}"
        )
        return NotificationResult.SUCCESS


@dataclass(slots=True)
class EmailChannel(NotificationChannel):
    _channel_type: ChannelType = ChannelType.EMAIL
    _to_addresses: tuple[str, ...] = ()
    _from_address: str = "titan@example.com"
    _smtp_host: str = "localhost"
    _smtp_port: int = 25

    @property
    def channel_type(self) -> ChannelType:
        return self._channel_type

    def send(self, alert: Alert) -> NotificationResult:
        try:
            self._send_email(alert)
            return NotificationResult.SUCCESS
        except Exception as exc:
            raise AlertingDispatchError(f"Email channel failed: {exc}") from exc

    def _send_email(self, alert: Alert) -> None:
        msg = "EmailChannel not configured: SMTP settings required"
        raise AlertingDispatchError(msg)


@dataclass(slots=True)
class TelegramChannel(NotificationChannel):
    _channel_type: ChannelType = ChannelType.TELEGRAM
    _bot_token: str = ""
    _chat_id: str = ""

    @property
    def channel_type(self) -> ChannelType:
        return self._channel_type

    def send(self, alert: Alert) -> NotificationResult:
        try:
            self._send_telegram(alert)
            return NotificationResult.SUCCESS
        except Exception as exc:
            raise AlertingDispatchError(f"Telegram channel failed: {exc}") from exc

    def _send_telegram(self, alert: Alert) -> None:
        msg = "TelegramChannel not configured: bot token required"
        raise AlertingDispatchError(msg)


@dataclass(slots=True)
class SlackChannel(NotificationChannel):
    _channel_type: ChannelType = ChannelType.SLACK
    _webhook_url: str = ""
    _channel: str = "#titan-alerts"

    @property
    def channel_type(self) -> ChannelType:
        return self._channel_type

    def send(self, alert: Alert) -> NotificationResult:
        try:
            self._send_slack(alert)
            return NotificationResult.SUCCESS
        except Exception as exc:
            raise AlertingDispatchError(f"Slack channel failed: {exc}") from exc

    def _send_slack(self, alert: Alert) -> None:
        msg = "SlackChannel not configured: webhook URL required"
        raise AlertingDispatchError(msg)


@dataclass(slots=True)
class WebhookChannel(NotificationChannel):
    _channel_type: ChannelType = ChannelType.WEBHOOK
    _url: str = ""
    _headers: Mapping[str, str] = field(default_factory=dict)
    _timeout_seconds: float = 10.0

    @property
    def channel_type(self) -> ChannelType:
        return self._channel_type

    def send(self, alert: Alert) -> NotificationResult:
        try:
            self._send_webhook(alert)
            return NotificationResult.SUCCESS
        except Exception as exc:
            raise AlertingDispatchError(f"Webhook channel failed: {exc}") from exc

    def _send_webhook(self, alert: Alert) -> None:
        msg = "WebhookChannel not configured: URL required"
        raise AlertingDispatchError(msg)


@dataclass(slots=True)
class ChannelManager:
    _channels: dict[ChannelType, NotificationChannel] = field(
        default_factory=dict, init=False
    )
    _configs: dict[ChannelType, ChannelConfig] = field(default_factory=dict, init=False)
    _max_retries: int = 3
    _lock: Lock = field(default_factory=Lock, init=False)

    def register_channel(
        self,
        channel: NotificationChannel,
        config: ChannelConfig | None = None,
    ) -> None:
        with self._lock:
            ct = channel.channel_type
            if ct in self._channels:
                raise AlertingChannelError(
                    f"Channel '{ct.value}' is already registered."
                )
            self._channels[ct] = channel
            self._configs[ct] = config or ChannelConfig(channel_type=ct)

    def unregister_channel(self, channel_type: ChannelType) -> None:
        with self._lock:
            if channel_type not in self._channels:
                raise AlertingChannelError(
                    f"Channel '{channel_type.value}' is not registered."
                )
            del self._channels[channel_type]
            del self._configs[channel_type]

    def get_channel(self, channel_type: ChannelType) -> NotificationChannel | None:
        with self._lock:
            return self._channels.get(channel_type)

    def dispatch(self, alert: Alert) -> tuple[NotificationAttempt, ...]:
        attempts: list[NotificationAttempt] = []
        with self._lock:
            channels = dict(self._channels)
            configs = dict(self._configs)

        for ct, channel in channels.items():
            config = configs.get(ct)
            if config is None:
                continue
            if not config.enabled:
                continue
            if level_rank(alert.level) < level_rank(config.min_level):
                continue

            attempt = self._dispatch_to_channel(channel, alert)
            attempts.append(attempt)

        return tuple(attempts)

    def _dispatch_to_channel(
        self,
        channel: NotificationChannel,
        alert: Alert,
    ) -> NotificationAttempt:
        for attempt_num in range(self._max_retries + 1):
            try:
                result = channel.send(alert)
                return NotificationAttempt(
                    channel=channel.channel_type,
                    result=result,
                    retry_count=attempt_num,
                )
            except AlertingDispatchError as exc:
                if attempt_num < self._max_retries:
                    continue
                return NotificationAttempt(
                    channel=channel.channel_type,
                    result=NotificationResult.FAILED,
                    error=str(exc),
                    retry_count=attempt_num,
                )
            except Exception as exc:
                error_msg = f"Unexpected error: {exc}"
                if attempt_num < self._max_retries:
                    continue
                return NotificationAttempt(
                    channel=channel.channel_type,
                    result=NotificationResult.FAILED,
                    error=error_msg,
                    retry_count=attempt_num,
                )

        return NotificationAttempt(
            channel=channel.channel_type,
            result=NotificationResult.FAILED,
            error="Max retries exceeded",
            retry_count=self._max_retries,
        )

    def registered_channels(self) -> tuple[ChannelType, ...]:
        with self._lock:
            return tuple(sorted(self._channels.keys(), key=lambda x: x.value))

    def reset(self) -> None:
        with self._lock:
            self._channels.clear()
            self._configs.clear()
