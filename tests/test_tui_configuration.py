"""Tests for the TITAN TUI Configuration & Deployment screen and models."""

import json
from dataclasses import asdict, is_dataclass
from typing import Any

import pytest
from textual.app import App

from titan.tui.layout import (
    _read_backup,
    _read_configuration,
    _read_deployment,
    _read_deployment_history,
    _read_environment,
    _read_services,
    _read_versions,
    build_configuration_state,
)
from titan.tui.models import (
    BackupInfo,
    ConfigurationInfo,
    ConfigurationScreenState,
    DeploymentHistoryEntry,
    DeploymentInfo,
    EnvironmentInfo,
    ServiceStatusEntry,
    VersionInfo,
)
from titan.tui.screens.configuration import ConfigurationScreen
from titan.tui.widgets.configuration import (
    BackupWidget,
    ConfigurationWidget,
    DeploymentHistoryWidget,
    DeploymentWidget,
    EnvironmentWidget,
    ServicesWidget,
    VersionWidget,
    _deployment_status_class,
    _health_class,
    _validation_class,
)

# ─── Model Tests ──────────────────────────────────────────────────────────────


class TestConfigurationModels:
    """Test Configuration & Deployment DTOs."""

    @pytest.mark.parametrize(
        "field",
        ["profile", "sources", "log_level", "pipeline_interval", "validation_status"],
    )
    def test_configuration_info_has_field(self, field: str) -> None:
        assert hasattr(ConfigurationInfo(), field)

    def test_configuration_info_is_dataclass(self) -> None:
        assert is_dataclass(ConfigurationInfo)

    def test_configuration_info_defaults(self) -> None:
        info = ConfigurationInfo()
        assert info.profile == ""
        assert info.sources == ()
        assert info.log_level == ""
        assert info.pipeline_interval == ""
        assert info.validation_status == ""

    def test_configuration_info_frozen(self) -> None:
        info = ConfigurationInfo()
        with pytest.raises(Exception):
            info.profile = "dev"  # type: ignore

    def test_configuration_info_slots(self) -> None:
        info = ConfigurationInfo()
        assert not hasattr(info, "__dict__")

    def test_configuration_info_json(self) -> None:
        info = ConfigurationInfo(profile="prod", sources=("file", "env"))
        assert json.loads(json.dumps(asdict(info)))["profile"] == "prod"

    @pytest.mark.parametrize(
        "field",
        ["name", "directories_verified", "secrets_available", "validation_status"],
    )
    def test_environment_info_has_field(self, field: str) -> None:
        assert hasattr(EnvironmentInfo(), field)

    def test_environment_info_is_dataclass(self) -> None:
        assert is_dataclass(EnvironmentInfo)

    def test_environment_info_defaults(self) -> None:
        info = EnvironmentInfo()
        assert info.name == ""
        assert info.directories_verified is False
        assert info.secrets_available is False
        assert info.validation_status == ""

    def test_environment_info_frozen(self) -> None:
        info = EnvironmentInfo()
        with pytest.raises(Exception):
            info.name = "dev"  # type: ignore

    def test_environment_info_slots(self) -> None:
        info = EnvironmentInfo()
        assert not hasattr(info, "__dict__")

    def test_environment_info_json(self) -> None:
        info = EnvironmentInfo(name="staging")
        assert json.loads(json.dumps(asdict(info)))["name"] == "staging"

    @pytest.mark.parametrize(
        "field", ["status", "uptime", "start_time", "health_status", "startup_duration"]
    )
    def test_deployment_info_has_field(self, field: str) -> None:
        assert hasattr(DeploymentInfo(), field)

    def test_deployment_info_is_dataclass(self) -> None:
        assert is_dataclass(DeploymentInfo)

    def test_deployment_info_defaults(self) -> None:
        info = DeploymentInfo()
        assert info.status == ""
        assert info.uptime == ""
        assert info.start_time == ""
        assert info.health_status == ""
        assert info.startup_duration == ""

    def test_deployment_info_frozen(self) -> None:
        info = DeploymentInfo()
        with pytest.raises(Exception):
            info.status = "running"  # type: ignore

    def test_deployment_info_slots(self) -> None:
        info = DeploymentInfo()
        assert not hasattr(info, "__dict__")

    def test_deployment_info_json(self) -> None:
        info = DeploymentInfo(status="stopped")
        assert json.loads(json.dumps(asdict(info)))["status"] == "stopped"

    @pytest.mark.parametrize("field", ["name", "status", "latency_ms", "message"])
    def test_service_status_entry_has_field(self, field: str) -> None:
        assert hasattr(ServiceStatusEntry(), field)

    def test_service_status_entry_is_dataclass(self) -> None:
        assert is_dataclass(ServiceStatusEntry)

    def test_service_status_entry_defaults(self) -> None:
        info = ServiceStatusEntry()
        assert info.name == ""
        assert info.status == ""
        assert info.latency_ms == ""
        assert info.message == ""

    def test_service_status_entry_frozen(self) -> None:
        info = ServiceStatusEntry()
        with pytest.raises(Exception):
            info.name = "db"  # type: ignore

    def test_service_status_entry_slots(self) -> None:
        info = ServiceStatusEntry()
        assert not hasattr(info, "__dict__")

    def test_service_status_entry_json(self) -> None:
        info = ServiceStatusEntry(name="cache", status="healthy")
        assert json.loads(json.dumps(asdict(info)))["status"] == "healthy"

    @pytest.mark.parametrize(
        "field",
        ["version", "build_number", "git_commit", "git_branch", "python_version"],
    )
    def test_version_info_has_field(self, field: str) -> None:
        assert hasattr(VersionInfo(), field)

    def test_version_info_is_dataclass(self) -> None:
        assert is_dataclass(VersionInfo)

    def test_version_info_defaults(self) -> None:
        info = VersionInfo()
        assert info.version == ""
        assert info.build_number == ""
        assert info.git_commit == ""
        assert info.git_branch == ""
        assert info.python_version == ""

    def test_version_info_frozen(self) -> None:
        info = VersionInfo()
        with pytest.raises(Exception):
            info.version = "1.0.0"  # type: ignore

    def test_version_info_slots(self) -> None:
        info = VersionInfo()
        assert not hasattr(info, "__dict__")

    def test_version_info_json(self) -> None:
        info = VersionInfo(version="1.0.1")
        assert json.loads(json.dumps(asdict(info)))["version"] == "1.0.1"

    @pytest.mark.parametrize(
        "field",
        [
            "last_backup_id",
            "last_backup_time",
            "components_backed_up",
            "total_files",
            "status",
        ],
    )
    def test_backup_info_has_field(self, field: str) -> None:
        assert hasattr(BackupInfo(), field)

    def test_backup_info_is_dataclass(self) -> None:
        assert is_dataclass(BackupInfo)

    def test_backup_info_defaults(self) -> None:
        info = BackupInfo()
        assert info.last_backup_id == ""
        assert info.last_backup_time == ""
        assert info.components_backed_up == 0
        assert info.total_files == 0
        assert info.status == ""

    def test_backup_info_frozen(self) -> None:
        info = BackupInfo()
        with pytest.raises(Exception):
            info.last_backup_id = "123"  # type: ignore

    def test_backup_info_slots(self) -> None:
        info = BackupInfo()
        assert not hasattr(info, "__dict__")

    def test_backup_info_json(self) -> None:
        info = BackupInfo(total_files=10)
        assert json.loads(json.dumps(asdict(info)))["total_files"] == 10

    @pytest.mark.parametrize(
        "field", ["timestamp_str", "action", "status", "version", "duration"]
    )
    def test_deployment_history_entry_has_field(self, field: str) -> None:
        assert hasattr(DeploymentHistoryEntry(), field)

    def test_deployment_history_entry_is_dataclass(self) -> None:
        assert is_dataclass(DeploymentHistoryEntry)

    def test_deployment_history_entry_defaults(self) -> None:
        info = DeploymentHistoryEntry()
        assert info.timestamp_str == ""
        assert info.action == ""
        assert info.status == ""
        assert info.version == ""
        assert info.duration == ""

    def test_deployment_history_entry_frozen(self) -> None:
        info = DeploymentHistoryEntry()
        with pytest.raises(Exception):
            info.action = "start"  # type: ignore

    def test_deployment_history_entry_slots(self) -> None:
        info = DeploymentHistoryEntry()
        assert not hasattr(info, "__dict__")

    def test_deployment_history_entry_json(self) -> None:
        info = DeploymentHistoryEntry(action="restart")
        assert json.loads(json.dumps(asdict(info)))["action"] == "restart"

    @pytest.mark.parametrize(
        "field",
        [
            "configuration",
            "environment",
            "deployment",
            "services",
            "version",
            "backup",
            "history",
            "last_refresh",
        ],
    )
    def test_configuration_screen_state_has_field(self, field: str) -> None:
        assert hasattr(ConfigurationScreenState(), field)

    def test_configuration_screen_state_is_dataclass(self) -> None:
        assert is_dataclass(ConfigurationScreenState)

    def test_configuration_screen_state_defaults(self) -> None:
        info = ConfigurationScreenState()
        assert isinstance(info.configuration, ConfigurationInfo)
        assert isinstance(info.environment, EnvironmentInfo)
        assert isinstance(info.deployment, DeploymentInfo)
        assert info.services == ()
        assert isinstance(info.version, VersionInfo)
        assert isinstance(info.backup, BackupInfo)
        assert info.history == ()
        assert info.last_refresh == ""

    def test_configuration_screen_state_frozen(self) -> None:
        info = ConfigurationScreenState()
        with pytest.raises(Exception):
            info.last_refresh = "10:00:00"  # type: ignore

    def test_configuration_screen_state_slots(self) -> None:
        info = ConfigurationScreenState()
        assert not hasattr(info, "__dict__")


# ─── CSS Helper Tests ─────────────────────────────────────────────────────────


class TestConfigurationCSSHelpers:
    """Test widget CSS helper functions."""

    @pytest.mark.parametrize(
        "status, expected",
        [
            ("Valid", "value-valid"),
            ("invalid", "value-invalid"),
            ("WARNINGS", "value-warnings"),
            ("unknown", "default-class"),
            ("", "default-class"),
        ],
    )
    def test_validation_class(self, status: str, expected: str) -> None:
        assert _validation_class(status) == expected

    @pytest.mark.parametrize(
        "status, expected",
        [
            ("running", "value-running"),
            ("stopped", "value-stopped"),
            ("error", "value-error"),
            ("failed", "value-error"),
            ("unknown", "default-class"),
            ("", "default-class"),
        ],
    )
    def test_deployment_status_class(self, status: str, expected: str) -> None:
        assert _deployment_status_class(status) == expected

    @pytest.mark.parametrize(
        "status, expected",
        [
            ("healthy", "value-healthy"),
            ("degraded", "value-degraded"),
            ("unhealthy", "value-unhealthy"),
            ("offline", "value-offline"),
            ("unknown", "default-class"),
            ("", "default-class"),
        ],
    )
    def test_health_class(self, status: str, expected: str) -> None:
        assert _health_class(status) == expected


# ─── Widget Tests ─────────────────────────────────────────────────────────────


class TestConfigurationWidget:
    def test_init(self) -> None:
        w = ConfigurationWidget()
        assert w._info == ConfigurationInfo()
        assert w.classes is None or "widget" not in w.classes  # dummy test
        assert w.name is None or isinstance(w.name, str)  # dummy test

    def test_configuration_widget_type(self) -> None:
        w = ConfigurationWidget()
        from textual.widget import Widget

        assert isinstance(w, Widget)

    def test_compose(self) -> None:
        w = ConfigurationWidget()
        composed = list(w.compose())
        assert len(composed) == 5

    def test_update_data_pre_compose(self) -> None:
        w = ConfigurationWidget()
        w.update_data(ConfigurationInfo(profile="prod"))
        assert w._info.profile == "prod"

    def test_render(self) -> None:
        w = ConfigurationWidget()
        assert w.render() == ""

    @pytest.mark.asyncio
    async def test_update_data_post_compose(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ConfigurationWidget()

        app = DummyApp()
        async with app.run_test():
            w = app.query_one(ConfigurationWidget)
            w.update_data(ConfigurationInfo(profile="prod", validation_status="valid"))
            assert w._info.profile == "prod"


class TestEnvironmentWidget:
    def test_init(self) -> None:
        w = EnvironmentWidget()
        assert w._info == EnvironmentInfo()

    def test_environment_widget_type(self) -> None:
        w = EnvironmentWidget()
        from textual.widget import Widget

        assert isinstance(w, Widget)

    def test_compose(self) -> None:
        w = EnvironmentWidget()
        composed = list(w.compose())
        assert len(composed) == 5

    def test_update_data_pre_compose(self) -> None:
        w = EnvironmentWidget()
        w.update_data(EnvironmentInfo(name="staging"))
        assert w._info.name == "staging"

    def test_render(self) -> None:
        w = EnvironmentWidget()
        assert w.render() == ""


class TestDeploymentWidget:
    def test_init(self) -> None:
        w = DeploymentWidget()
        assert w._info == DeploymentInfo()

    def test_deployment_widget_type(self) -> None:
        w = DeploymentWidget()
        from textual.widget import Widget

        assert isinstance(w, Widget)

    def test_compose(self) -> None:
        w = DeploymentWidget()
        composed = list(w.compose())
        assert len(composed) == 5

    def test_update_data_pre_compose(self) -> None:
        w = DeploymentWidget()
        w.update_data(DeploymentInfo(status="running"))
        assert w._info.status == "running"

    def test_render(self) -> None:
        w = DeploymentWidget()
        assert w.render() == ""


class TestVersionWidget:
    def test_init(self) -> None:
        w = VersionWidget()
        assert w._info == VersionInfo()

    def test_version_widget_type(self) -> None:
        w = VersionWidget()
        from textual.widget import Widget

        assert isinstance(w, Widget)

    def test_compose(self) -> None:
        w = VersionWidget()
        composed = list(w.compose())
        assert len(composed) == 5

    def test_update_data_pre_compose(self) -> None:
        w = VersionWidget()
        w.update_data(VersionInfo(version="1.2.3"))
        assert w._info.version == "1.2.3"

    def test_render(self) -> None:
        w = VersionWidget()
        assert w.render() == ""


class TestBackupWidget:
    def test_init(self) -> None:
        w = BackupWidget()
        assert w._info == BackupInfo()

    def test_backup_widget_type(self) -> None:
        w = BackupWidget()
        from textual.widget import Widget

        assert isinstance(w, Widget)

    def test_compose(self) -> None:
        w = BackupWidget()
        composed = list(w.compose())
        assert len(composed) == 4

    def test_update_data_pre_compose(self) -> None:
        w = BackupWidget()
        w.update_data(BackupInfo(last_backup_id="abc"))
        assert w._info.last_backup_id == "abc"

    def test_render(self) -> None:
        w = BackupWidget()
        assert w.render() == ""


class TestServicesWidget:
    def test_init(self) -> None:
        w = ServicesWidget()
        assert w._entries == ()

    def test_compose(self) -> None:
        w = ServicesWidget()
        composed = list(w.compose())
        assert len(composed) == 1

    def test_update_data_pre_compose(self) -> None:
        w = ServicesWidget()
        w.update_data((ServiceStatusEntry(name="db"),))
        assert len(w._entries) == 1
        assert len(w._rows) == 0

    def test_render(self) -> None:
        w = ServicesWidget()
        assert w.render() == ""

    @pytest.mark.asyncio
    async def test_update_data_empty(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ServicesWidget()

        app = DummyApp()
        async with app.run_test():
            w = app.query_one(ServicesWidget)
            w.update_data(())
            assert len(w._rows) == 1

    @pytest.mark.asyncio
    async def test_update_data_populated(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ServicesWidget()

        app = DummyApp()
        async with app.run_test():
            w = app.query_one(ServicesWidget)
            w.update_data(
                (
                    ServiceStatusEntry(
                        name="db", status="healthy", message="ok", latency_ms="5"
                    ),
                )
            )
            assert len(w._rows) == 1


class TestDeploymentHistoryWidget:
    def test_init(self) -> None:
        w = DeploymentHistoryWidget()
        assert w._entries == ()

    def test_compose(self) -> None:
        w = DeploymentHistoryWidget()
        composed = list(w.compose())
        assert len(composed) == 1

    def test_update_data_pre_compose(self) -> None:
        w = DeploymentHistoryWidget()
        w.update_data((DeploymentHistoryEntry(action="start"),))
        assert len(w._entries) == 1
        assert len(w._rows) == 0

    def test_render(self) -> None:
        w = DeploymentHistoryWidget()
        assert w.render() == ""

    @pytest.mark.asyncio
    async def test_update_data_empty(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield DeploymentHistoryWidget()

        app = DummyApp()
        async with app.run_test():
            w = app.query_one(DeploymentHistoryWidget)
            w.update_data(())
            assert len(w._rows) == 1

    @pytest.mark.asyncio
    async def test_update_data_populated(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield DeploymentHistoryWidget()

        app = DummyApp()
        async with app.run_test():
            w = app.query_one(DeploymentHistoryWidget)
            w.update_data(
                (
                    DeploymentHistoryEntry(
                        timestamp_str="10:00",
                        action="restart",
                        status="success",
                        version="1.0",
                    ),
                )
            )
            assert len(w._rows) == 1


# ─── Layout Reader Tests ──────────────────────────────────────────────────────


class TestConfigurationReaders:
    """Test layout readers with exceptions and defaults."""

    def test_read_configuration_exception(self, monkeypatch: Any) -> None:
        def mock_get(*args: Any, **kwargs: Any):
            raise RuntimeError("Mock Error")

        monkeypatch.setattr("titan.cli.common.get_config_manager", mock_get)
        res = _read_configuration()
        assert isinstance(res, ConfigurationInfo)
        assert res.profile == ""

    def test_read_environment_exception(self, monkeypatch: Any) -> None:
        def mock_get(*args: Any, **kwargs: Any):
            raise RuntimeError("Mock Error")

        monkeypatch.setattr("titan.cli.common.get_deployment_manager", mock_get)
        res = _read_environment()
        assert isinstance(res, EnvironmentInfo)
        assert res.name == ""

    def test_read_deployment_exception(self, monkeypatch: Any) -> None:
        def mock_get(*args: Any, **kwargs: Any):
            raise RuntimeError("Mock Error")

        monkeypatch.setattr("titan.cli.common.get_deployment_manager", mock_get)
        res = _read_deployment()
        assert isinstance(res, DeploymentInfo)
        assert res.status == ""

    def test_read_services_exception(self, monkeypatch: Any) -> None:
        def mock_get(*args: Any, **kwargs: Any):
            raise RuntimeError("Mock Error")

        monkeypatch.setattr("titan.cli.common.get_deployment_manager", mock_get)
        res = _read_services()
        assert res == ()

    def test_read_versions_exception(self, monkeypatch: Any) -> None:
        def mock_get(*args: Any, **kwargs: Any):
            raise RuntimeError("Mock Error")

        monkeypatch.setattr("titan.cli.common.get_deployment_manager", mock_get)
        res = _read_versions()
        assert isinstance(res, VersionInfo)
        assert res.version == ""

    def test_read_backup_default(self) -> None:
        res = _read_backup()
        assert isinstance(res, BackupInfo)

    def test_read_deployment_history_default(self) -> None:
        res = _read_deployment_history()
        assert res == ()

    def test_build_configuration_state_exception(self, monkeypatch: Any) -> None:
        def mock_get(*args: Any, **kwargs: Any):
            raise RuntimeError("Mock Error")

        monkeypatch.setattr("titan.cli.common.get_config_manager", mock_get)
        monkeypatch.setattr("titan.cli.common.get_deployment_manager", mock_get)
        state = build_configuration_state()
        assert isinstance(state, ConfigurationScreenState)
        assert state.configuration.profile == ""
        assert state.environment.name == ""
        assert state.deployment.status == ""
        assert state.last_refresh != ""


# ─── Screen Tests ─────────────────────────────────────────────────────────────


class TestConfigurationScreen:
    """Test ConfigurationScreen lifecycle and bindings."""

    @pytest.mark.asyncio
    async def test_screen_init(self) -> None:
        s = ConfigurationScreen()
        assert s._state == ConfigurationScreenState()
        assert s._state_builder is None

    @pytest.mark.asyncio
    async def test_screen_compose(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ConfigurationScreen()

        app = DummyApp()
        async with app.run_test():
            s = app.query_one(ConfigurationScreen)
            assert len(s.children) >= 2

    @pytest.mark.asyncio
    async def test_screen_state_builder(self) -> None:
        s = ConfigurationScreen()

        def mock_builder():
            return ConfigurationScreenState(last_refresh="123")

        s.set_state_builder(mock_builder)
        assert s._state_builder == mock_builder
        s._refresh_state()
        assert s.state.last_refresh == "123"

    @pytest.mark.asyncio
    async def test_screen_state_builder_exception(self) -> None:
        s = ConfigurationScreen()

        def mock_builder():
            raise RuntimeError("Mock error")

        s.set_state_builder(mock_builder)
        s._refresh_state()
        assert isinstance(s.state, ConfigurationScreenState)
        assert s.state.last_refresh == ""

    @pytest.mark.asyncio
    async def test_screen_mount_refresh(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ConfigurationScreen()

        app = DummyApp()
        async with app.run_test():
            s = app.query_one(ConfigurationScreen)
            s._tick_refresh()
            assert s.state is not None

    @pytest.mark.asyncio
    async def test_screen_actions(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ConfigurationScreen()

        app = DummyApp()
        async with app.run_test():
            s = app.query_one(ConfigurationScreen)
            s.action_refresh()
            s.action_scroll_up()
            s.action_scroll_down()
            s.action_scroll_up_line()
            s.action_scroll_down_line()
            s.action_scroll_top()
            s.action_scroll_bottom()

    @pytest.mark.asyncio
    async def test_screen_actions_no_scroll(self) -> None:
        s = ConfigurationScreen()
        s.action_scroll_up()
        s.action_scroll_down()
        s.action_scroll_up_line()
        s.action_scroll_down_line()
        s.action_scroll_top()
        s.action_scroll_bottom()
        assert True  # Did not crash

    @pytest.mark.asyncio
    async def test_screen_back_action(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ConfigurationScreen()

        app = DummyApp()
        async with app.run_test():
            s = app.query_one(ConfigurationScreen)
            s.action_back()
            # If there was a previous screen, it would pop. For tests, checking no crash.

    @pytest.mark.asyncio
    async def test_screen_update_widgets(self) -> None:
        class DummyApp(App):
            def compose(self):
                yield ConfigurationScreen()

        app = DummyApp()
        async with app.run_test():
            s = app.query_one(ConfigurationScreen)
            s._update_widgets()
            assert s._config_widget is not None
            assert s._services_widget is not None
