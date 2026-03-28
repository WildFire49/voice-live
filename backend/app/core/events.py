from enum import Enum


class SessionState(str, Enum):
    CONNECTING = "connecting"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
