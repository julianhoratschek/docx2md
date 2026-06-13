from enum import IntFlag
from typing import NamedTuple


class ClosingState(IntFlag):
    Opening     = 0b00
    Closing     = 0b01
    SelfClosing = 0b10


class Tag(NamedTuple):
    name            : str               = ""
    attr            : dict[str, str]    = {}
    closing_state   : ClosingState      = ClosingState.Opening
    start           : int               = 0
    end             : int               = 0



