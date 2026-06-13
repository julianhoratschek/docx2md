from typing import override

from .converter import TagConverter, DocxProtocol
from ..style import STYLE_TAGS
from ..tag import Tag


class TagMdConverter(TagConverter):
    """
    Standard converter to convert docx to md

    :ivar in_header:    True if currently processing table header
    :ivar col_count:    Counts header cols of current table
    :ivar output   :    Text blob used as conversion result
    """

    def __init__(self, owner: DocxProtocol):
        super().__init__(owner)

        self.in_header: bool = False
        self.col_count: int  = 0
        self.output   : str  = ""


    @override
    def convert(self, tag: Tag):
        if not self.process_style_stack(tag):
            return

        if tag.name in STYLE_TAGS:
            return self.convert_style_tag(tag)

        match tag.name:
            # Insert paragraph after w:p element
            case "w:p" if tag.closing_state:
                self.output += "\n\n"

            # Insert line break
            case "w:br":
                self.output += "\\\n"

            # Insert content at beginning of w:t
            case "w:t" if not tag.closing_state:
                self.output += self.style.wrap(
                    self.owner.get_content(), self.style_mapping)

            # Insert list bullets
            case "w:listPr" | "w:numPr" if tag.closing_state:
                self.output += "- "

            case "w:ilvl":
                try:
                    lvl = int(tag.attr["w:val"])
                    self.output += "\t" * lvl
                except ValueError:
                    self.owner.error("Expected numerical indent value for list")
                except KeyError:
                    self.owner.error("Expected w:val in w:ilvl")

            case "w:tblHeader":
                self.in_header = True
                self.col_count = 0

            # Insert | on opening tags
            case "w:tc" if not tag.closing_state:
                if self.in_header:
                    self.col_count += 1
                self.output += "|"

            # Insert last col | and newline on closing tr
            case "w:tr" if tag.closing_state:
                res = "|\n"
                if self.in_header:
                    self.in_header = False
                    res += "|" + ("---|" * self.col_count) + "\n"
                self.output += res

            case _: pass

    @override
    def get_result(self) -> str:
        return self.output
