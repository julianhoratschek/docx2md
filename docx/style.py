from enum import IntFlag
from dataclasses import dataclass

from .tag import Tag


class Styling(IntFlag):
    NoStyle     = 0b00000
    Italic      = 0b00001
    Bold        = 0b00010
    Underline   = 0b00100
    Striked     = 0b01000
    Highlight   = 0b10000

    def wrap(self, text: str, style_mapping: dict[Styling, tuple[str, str]]) -> str:
        styles = STYLE_DEFAULT | style_mapping

        for style in self:
            b, e = styles[style]
            text = f"{b}{text}{e}"

        return text


STYLE_DEFAULT = {
    Styling.Bold: ("**", "**"),
    Styling.Italic: ("_", "_"),
    Styling.Underline: ("<u>", "</u>"),
    Styling.Striked: ("~~", "~~"),
    Styling.Highlight: ("==", "==") 
}


STYLE_TAGS = {
    "w:b"           : Styling.Bold,
    "w:i"           : Styling.Italic,
    "w:u"           : Styling.Underline,
    "w:strike"      : Styling.Striked,
    "w:highlight"   : Styling.Highlight
}


@dataclass
class StyledSection:
    tag     : Tag
    style   : Styling   = Styling.NoStyle
