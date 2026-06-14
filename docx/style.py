from enum import IntFlag
from dataclasses import dataclass

from .tag import Tag


class Styling(IntFlag):
    NoStyle   = 0
    Italic    = 1
    Bold      = 2
    Underline = 4
    Striked   = 8
    Highlight = 16

    def wrap(self, text: str,
             style_mapping: dict[Styling, tuple[str, str]] | None = None) -> str:
        """
        Wraps `text` in styling tags according to all flags in `self`. Styling
        tags can be provided by `style_mapping`.

        :param text         :   Text to wrap in style-tags
        :param style_mapping:   optional, maps `Styling` to opening/close tags
        :returns            :   `text` wrapped in one or multiple tags
        """

        styles = STYLE_DEFAULT | (style_mapping or {})
        for style in self:
            b, e = styles[style]
            text = f"{b}{text}{e}"

        return text


# Default for Styling.wrap
STYLE_DEFAULT = {
    Styling.Bold     : ("**", "**"),
    Styling.Italic   : ("_", "_"),
    Styling.Underline: ("<u>", "</u>"),
    Styling.Striked  : ("~~", "~~"),
    Styling.Highlight: ("==", "==") 
}


STYLE_TAGS = {
    "w:b"        : Styling.Bold,
    "w:i"        : Styling.Italic,
    "w:u"        : Styling.Underline,
    "w:strike"   : Styling.Striked,
    "w:highlight": Styling.Highlight
}


@dataclass
class StyledSection:
    tag  : Tag
    style: Styling = Styling.NoStyle
