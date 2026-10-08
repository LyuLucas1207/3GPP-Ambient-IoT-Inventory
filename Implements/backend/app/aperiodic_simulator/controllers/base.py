"""Controller interface for the aperiodic-paging engine.

A controller decides the next round's action ``(L, p)`` from the round
observation of Eq. (5) only:

    S1, S2a, S2b  identified devices per type in the previous round
    I, C          observed idle / collided AOs in the previous round
    L, p          the previous action

plus ``decoded`` (observed single-success AOs, = L*F - I - C), which is a
function of the same observation. Hidden quantities (true backlog, energies,
C2, physical occupancy) are never passed to a controller.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

OBSERVATION_KEYS = ("S1", "S2a", "S2b", "I", "C", "L", "p", "decoded")


@dataclass
class Action:
    L: int
    p: float
    info: dict = field(default_factory=dict)  # controller diagnostics (estimates, m, q, ...)


class Controller(ABC):
    name: str = "base"
    adapts_L: bool = False
    adapts_p: bool = True

    def __init__(self, F: int, L_max: int, p_floor: float):
        self.F = F
        self.L_max = L_max
        self.p_floor = p_floor

    def clip(self, L: int, p: float) -> tuple[int, float]:
        return int(min(max(int(L), 1), self.L_max)), float(min(max(p, self.p_floor), 1.0))

    @abstractmethod
    def reset(self, L0: int, p0: float) -> Action:
        """Start a new episode and return the first action."""

    @abstractmethod
    def update(self, obs: dict) -> Action:
        """Return the next action from the previous round's observation."""
