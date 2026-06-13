from enum import IntFlag
from typing import NamedTuple


class ClosingState(IntFlag):
    Opening     = 0
    Closing     = 1
    SelfClosing = 2


class Tag(NamedTuple):
    """
    Bare information about matched ooxml-tag

    :ivar name         :    Tag name, e.g. "w:p"
    :ivar attr         :    Dictionaty of Attribute-Value-Pairs
    :ivar closing_state:    Flagging opening/closing tags
    :ivar start        :    Start of Tag Match in loaded xml
    :ivar end          :    End of Tag Match in loaded xml
    """

    name         : str            = ""
    attr         : dict[str, str] = {}
    closing_state: ClosingState   = ClosingState.Opening
    start        : int            = 0
    end          : int            = 0



