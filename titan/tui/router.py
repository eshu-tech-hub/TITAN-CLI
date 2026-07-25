"""TITAN TUI screen router.

Centralized routing for screen registration, lazy creation,
screen switching, and history stack. No screen should navigate
to another screen directly.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from textual.screen import Screen


class ScreenRouter:
    """Manages screen registration, creation, switching, and navigation history.

    Screens are registered by name with a factory callable. They are created
    lazily on first navigation. The history stack enables back-navigation.
    """

    def __init__(self, default: str = "dashboard") -> None:
        self._factories: dict[str, Callable[..., Screen]] = {}
        self._cache: dict[str, Screen] = {}
        self._history: deque[str] = deque()
        self._default = default
        self._current: str = default
        self._screen_names: list[str] = []

    @property
    def current(self) -> str:
        """Name of the currently active screen."""
        return self._current

    @property
    def default(self) -> str:
        """Name of the default screen."""
        return self._default

    @property
    def history(self) -> list[str]:
        """Snapshot of the navigation history stack."""
        return list(self._history)

    @property
    def screen_names(self) -> list[str]:
        """Ordered list of registered screen names."""
        return list(self._screen_names)

    def register(
        self,
        name: str,
        factory: Callable[..., Screen],
        *,
        is_default: bool = False,
    ) -> None:
        """Register a screen factory by name.

        Args:
            name: Unique screen identifier.
            factory: Callable that returns a new Screen instance.
            is_default: If True, set this as the default screen.
        """
        self._factories[name] = factory
        if name not in self._screen_names:
            self._screen_names.append(name)
        if is_default:
            self._default = name

    def create(self, name: str, **kwargs: Any) -> Screen:
        """Create a new screen instance by name.

        Args:
            name: Registered screen name.
            **kwargs: Forwarded to the factory.

        Returns:
            A new Screen instance.

        Raises:
            KeyError: If the screen name is not registered.
        """
        if name not in self._factories:
            raise KeyError(f"Screen not registered: {name}")
        return self._factories[name](**kwargs)

    def get_or_create(self, name: str, **kwargs: Any) -> Screen:
        """Get cached screen or create a new one.

        Screens are cached after first creation. Use invalidate()
        to force recreation.
        """
        if name not in self._cache:
            self._cache[name] = self.create(name, **kwargs)
        return self._cache[name]

    def invalidate(self, name: str | None = None) -> None:
        """Remove cached screen(s) so they are recreated on next access.

        Args:
            name: Specific screen to invalidate, or None for all.
        """
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(name, None)

    def navigate(self, name: str, **kwargs: Any) -> Screen:
        """Navigate to a screen, pushing the current one onto history.

        Returns the target screen instance.
        """
        if name not in self._factories:
            raise KeyError(f"Screen not registered: {name}")
        if name == self._default:
            self._history.clear()
        elif self._current != name:
            self._history.append(self._current)
        self._current = name
        return self.get_or_create(name, **kwargs)

    def go_back(self) -> Screen | None:
        """Navigate to the previous screen in history.

        Returns the previous screen, or None if history is empty
        or the previous screen is not registered.
        """
        if not self._history:
            return None
        prev = self._history.pop()
        if prev not in self._factories:
            self._current = self._default
            return None
        self._current = prev
        return self.get_or_create(prev)

    def can_go_back(self) -> bool:
        """Check if there is a previous screen to navigate to."""
        return len(self._history) > 0

    def reset_history(self) -> None:
        """Clear navigation history."""
        self._history.clear()
        self._current = self._default

    def get_screen_names(self) -> list[str]:
        """Return registered screen names in registration order."""
        return list(self._screen_names)
