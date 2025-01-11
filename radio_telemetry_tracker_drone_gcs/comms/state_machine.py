"""State machine for managing drone communication states."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal


class DroneState(Enum):
    """Enum representing possible drone states."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONFIGURING = auto()
    READY = auto()
    RUNNING = auto()
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
        self._current_state = DroneState.DISCONNECTED
        self._transition_handlers: dict[DroneState, Callable[[], None]] = {}
        self._error_handlers: dict[DroneState, Callable[[str], None]] = {}

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
            logging.error(error_msg)
            self.state_error.emit(error_msg)
            return

        old_state = self._current_state
        self._current_state = new_state
        logging.info("State transition: %s -> %s", old_state, new_state)

        if new_state in self._transition_handlers:
            try:
                self._transition_handlers[new_state]()
            except Exception as e:
                error_msg = f"Error in transition handler: {e}"
                logging.exception(error_msg)
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
                logging.exception("Error in error handler")

        self.state_error.emit(error_msg)
