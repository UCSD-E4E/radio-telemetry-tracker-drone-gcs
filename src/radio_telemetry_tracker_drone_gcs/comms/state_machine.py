"""State machine for managing drone communication states."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

class DroneState(Enum):
    """Enum representing possible drone states."""

    # Radio config states
    RADIO_CONFIG_INPUT = auto()
    RADIO_CONFIG_WAITING = auto()
    RADIO_CONFIG_TIMEOUT = auto()

    # Ping finder config states
    PING_FINDER_CONFIG_INPUT = auto()
    PING_FINDER_CONFIG_WAITING = auto()
    PING_FINDER_CONFIG_TIMEOUT = auto()

    # Start states
    START_INPUT = auto()
    START_WAITING = auto()
    START_TIMEOUT = auto()

    # Stop states
    STOP_INPUT = auto()
    STOP_WAITING = auto()
    STOP_TIMEOUT = auto()

    # Error state
    ERROR = auto()


@dataclass
class StateTransition:
    """Data class for state transition information."""

    from_state: DroneState
    to_state: DroneState
    success_message: str
    failure_message: str


class DroneStateMachine(QObject):
    """State machine for managing drone communication states."""

    # State change signals
    state_changed = pyqtSignal(DroneState)
    state_error = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize the state machine."""
        super().__init__()
        self._current_state = DroneState.RADIO_CONFIG_INPUT
        self._transition_handlers: dict[DroneState, Callable[[], None]] = {}
        self._error_handlers: dict[DroneState, Callable[[str], None]] = {}
        self._timeout_handlers: dict[DroneState, Callable[[], None]] = {}

    @property
    def current_state(self) -> DroneState:
        """Get the current state."""
        return self._current_state

    def register_transition_handler(
        self,
        state: DroneState,
        handler: Callable[[], None],
    ) -> None:
        """Register a handler for state transitions.

        Args:
            state: The state to handle transitions for
            handler: The handler function to call
        """
        self._transition_handlers[state] = handler

    def register_error_handler(self, state: DroneState, handler: Callable[[str], None]) -> None:
        """Register a handler for state errors.

        Args:
            state: The state to handle errors for
            handler: The handler function to call
        """
        self._error_handlers[state] = handler

    def register_timeout_handler(self, state: DroneState, handler: Callable[[], None]) -> None:
        """Register a handler for state timeouts.

        Args:
            state: The state to handle timeouts for
            handler: The handler function to call
        """
        self._timeout_handlers[state] = handler

    def handle_timeout(self) -> None:
        """Handle timeout in the current state."""
        current_state = self._current_state

        # Map waiting states to timeout states
        timeout_map = {
            DroneState.RADIO_CONFIG_WAITING: DroneState.RADIO_CONFIG_TIMEOUT,
            DroneState.PING_FINDER_CONFIG_WAITING: DroneState.PING_FINDER_CONFIG_TIMEOUT,
            DroneState.START_WAITING: DroneState.START_TIMEOUT,
            DroneState.STOP_WAITING: DroneState.STOP_TIMEOUT,
        }

        if current_state in timeout_map:
            self.transition_to(timeout_map[current_state])
            if current_state in self._timeout_handlers:
                try:
                    self._timeout_handlers[current_state]()
                except Exception:
                    logger.exception("Error in timeout handler")

    def transition_to(self, new_state: DroneState, transition: StateTransition | None = None) -> None:
        """Transition to a new state.

        Args:
            new_state: The state to transition to
            transition: Optional transition information
        """
        if transition and transition.from_state != self._current_state:
            error_msg = (
                f"Invalid state transition from {self._current_state} to {new_state}. "
                f"Expected from state: {transition.from_state}"
            )
            logger.error(error_msg)
            self.state_error.emit(error_msg)
            return

        old_state = self._current_state
        self._current_state = new_state
        logger.info("State transition: %s -> %s", old_state, new_state)

        if new_state in self._transition_handlers:
            try:
                self._transition_handlers[new_state]()
            except Exception as e:
                error_msg = f"Error in transition handler: {e}"
                logger.exception(error_msg)
                self.state_error.emit(error_msg)
                return

        self.state_changed.emit(new_state)

    def handle_error(self, error_msg: str) -> None:
        """Handle an error in the current state.

        Args:
            error_msg: The error message
        """
        if self._current_state in self._error_handlers:
            try:
                self._error_handlers[self._current_state](error_msg)
            except Exception:
                logger.exception("Error in error handler")

        self.state_error.emit(error_msg)
