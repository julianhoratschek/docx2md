from pathlib import Path
from typing import Literal, NamedTuple
from collections.abc import Iterator
from enum import IntFlag
from dataclasses import dataclass
import re
import zipfile
import sys


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



class Styling(IntFlag):
    NoStyle     = 0b00000
    Italic      = 0b00001
    Bold        = 0b00010
    Underline   = 0b00100
    Striked     = 0b01000
    Highlight   = 0b10000

    def wrap(self, text: str, tp: str = 'md') -> str:
        if tp not in ('md', 'html'):
            tp = 'md'

        for style in self:
            b, e = STYLE_STR[tp][style]
            text = f"{b}{text}{e}"

        return text


STYLE_STR = {
    "html": {
        Styling.Bold: ("<b>", "</b>"),
        Styling.Italic: ("<i>", "</i>"),
        Styling.Underline: ("<u>", "</u>"),
        Styling.Striked: ("<s>", "</s>"),
        Styling.Highlight: ("<mark>", "</mark>") 
    },

    "md": {
        Styling.Bold: ("**", "**"),
        Styling.Italic: ("_", "_"),
        Styling.Underline: ("<u>", "</u>"),
        Styling.Striked: ("~~", "~~"),
        Styling.Highlight: ("==", "==") 
    }
}


@dataclass
class StyledSection:
    tag     : Tag
    style   : Styling   = Styling.NoStyle


class TagConverter:
    def __init__(self, owner: DocxDocument):
        self.owner      : DocxDocument          = owner
        self.style_stack: list[StyledSection]   = []

    @property
    def style(self) -> Styling:
        """Recalculate complete style stack"""
        result = Styling.NoStyle
        for sect in self.style_stack:
            result |= sect.style
        return result


class TagMdConverter(TagConverter):
    def __init__(self, owner: DocxDocument):
        super().__init__(owner)

        self.in_header: bool = False
        self.col_count: int = 0


    def convert(self, tag: Tag):
        """Converts the current `self.tag` into markdown and saves it into
        `self.output`. <w:t> tags content will be read completely."""

        # Test for elements that can contain styling hints
        if tag.name in ("w:p", "w:r"):

            # Opening tag
            if not tag.closing_state:
                self.style_stack.append(StyledSection(tag))

            # Closing tag
            elif self.style_stack and tag.name == self.style_stack[-1].tag.name:
                self.style_stack.pop()

            else:
                err_msg = f"Unexpected closing tag {tag.name}"
                if self.style_stack:
                    err_msg += f", expected {self.style_stack[-1].tag.name}"
                self.owner.error(err_msg)
                return

        # Test for style hints

        styles = {
            "w:b"           : Styling.Bold,
            "w:i"           : Styling.Italic,
            "w:u"           : Styling.Underline,
            "w:strike"      : Styling.Striked,
            "w:highlight"   : Styling.Highlight
        }

        if tag.name in styles:
            if self.style_stack:
                self.style_stack[-1].style |= styles[tag.name]
            else:
                self.owner.error("Unexpected styling-tag")
            return

        # Test all other tags
                
        match tag.name:
            # Insert paragraph after w:p element
            case "w:p" if tag.closing_state:
                return "\n\n"

            # Insert line break
            case "w:br":
                return "\\\n"

            # Insert content at beginning of w:t
            case "w:t" if not tag.closing_state:
                return self.style.wrap(
                    self.owner.get_content(),
                    self.owner.output_type)

            # Insert list bullets
            # TODO: Numerical lists
            case "w:listPr" | "w:numPr" if tag.closing_state:
                return "- "

            case "w:ilvl":
                try:
                    lvl = int(tag.attr["w:val"])
                    return "\t" * lvl
                except ValueError:
                    self.owner.error("Expected numerical indent value for list")
                except KeyError:
                    self.owner.error("Expected w:val in w:ilvl")

            # TODO: Table as html
            case "w:tblHeader":
                self.in_header = True
                self.col_count = 0

            # Insert | on opening tags
            case "w:tc" if not tag.closing_state:
                if self.in_header:
                    self.col_count += 1
                return "|"

            # Insert last col | and newline on closing tr
            case "w:tr" if tag.closing_state:
                res = "|\n"
                if self.in_header:
                    self.in_header = False
                    res += "|" + ("---|" * self.col_count) + "\n"
                return res

            case _:
                pass
        return ""


class DocxDocument:
    def error(self, msg: str):
        print(f"[!] {self.tag.start}: {msg}")

    def __next_tag(self) -> bool:
        """Increments the internal iterator and reads `self.tag`"""

        try:
            tag_match = next(self.iter)
        except StopIteration:
            return False

        closing_state = ClosingState.Opening
        if tag_match["closing"]:
            closing_state |= ClosingState.Closing
        if tag_match["self_closing"]:
            closing_state |= ClosingState.SelfClosing

        attr_list: dict[str, str] = {
            m["name"]: m["value"]
            for m in self.attr_pattern.finditer(tag_match["attr"])
        } if tag_match["attr"] else {}

        self.tag = Tag(
            tag_match["tag"],
            attr_list,
            closing_state,
            tag_match.start(),
            tag_match.end())

        return True

    def get_content(self) -> str:
        """Get complete text between <w:t> and </w:t>"""

        begin = self.tag.end
        if not self.__next_tag():
            self.error("Unexpected End Of File, expected </w:t>")
            return ""

        if self.tag.name != "w:t":
            self.error("Unexpected closing Tag, expected </w:t>")
            return ""

        if not self.tag.closing_state:
            self.error("Unexpected opening tag <w:t>")
            return ""

        end = self.tag.start
        return self.xml[begin:end]


    def __convert_tag(self):
        """Converts the current `self.tag` into markdown and saves it into
        `self.output`. <w:t> tags content will be read completely."""

        # Test for elements that can contain styling hints
        if self.tag.name in ("w:p", "w:r"):

            # Opening tag
            if not self.tag.closing_state:
                self.style_stack.append(StyledSection(self.tag))

            # Closing tag
            elif self.style_stack and self.tag.name == self.style_stack[-1].tag.name:
                self.style_stack.pop()

            else:
                err_msg = f"Unexpected closing tag {self.tag.name}"
                if self.style_stack:
                    err_msg += f", expected {self.style_stack[-1].tag.name}"
                self.error(err_msg)
                return

        # Test for style hints

        styles = {
            "w:b"           : Styling.Bold,
            "w:i"           : Styling.Italic,
            "w:u"           : Styling.Underline,
            "w:strike"      : Styling.Striked,
            "w:highlight"   : Styling.Highlight
        }

        if self.tag.name in styles:
            if self.style_stack:
                self.style_stack[-1].style |= styles[self.tag.name]
            else:
                self.error("Unexpected styling-tag")
            return

        # Test all other tags
                
        match self.tag.name:
            # Insert paragraph after w:p element
            case "w:p" if self.tag.closing_state:
                self.output += "\n\n"

            # Insert line break
            case "w:br":
                self.output += "\\\n"

            # Insert content at beginning of w:t
            case "w:t" if not self.tag.closing_state:
                # self.output += self.__apply_style(self.__get_content())
                self.output += self.style.wrap(
                    self.__get_content(),
                    self.output_type)

            # Insert list bullets
            # TODO: Numerical lists
            case "w:listPr" | "w:numPr" if self.tag.closing_state:
                self.output += "- "

            case "w:ilvl":
                try:
                    lvl = int(self.tag.attr["w:val"])
                    self.output += "\t" * lvl
                except ValueError:
                    self.error("Expected numerical indent value for list")
                except KeyError:
                    self.error("Expected w:val in w:ilvl")

            # TODO: Table as html
            case "w:tblHeader":
                self.in_header = True
                self.col_count = 0

            # Insert | on opening tags
            case "w:tc" if not self.tag.closing_state:
                self.output += "|"
                if self.in_header:
                    self.col_count += 1

            # Insert last col | and newline on closing tr
            case "w:tr" if self.tag.closing_state:
                self.output += "|\n"
                if self.in_header:
                    self.in_header = False
                    self.output += "|" + ("---|" * self.col_count) + "\n"

            case _:
                pass


    def __init__(self, output_type: Literal["md", "html"] = "md"):
        self.xml            : str                       = ""

        self.tag_pattern    : re.Pattern[str]           = re.compile(
                r"<(?P<closing>/)?" + 
                r"(?P<tag>[\w:_\d]+)" +
                r"(?P<attr>\s+[^/>]*?)?" +
                r"(?P<self_closing>/)?>")
        self.attr_pattern   : re.Pattern[str]           = re.compile(
                r'(?P<name>[\w\d_:]+)="(?P<value>[^"]*)"')

        self.output         : str                       = ""
        self.in_header      : bool                      = False
        self.col_count      : int                       = 0

        self.iter           : Iterator[re.Match[str]]   = iter(())
        self.tag            : Tag                       = Tag()

        self.style_stack    : list[StyledSection]       = []
        self.output_type    : Literal["md", "html"]     = output_type if output_type in ("md", "html") else "md"




    def write(self, file_name: Path | str):
        with Path(file_name).open("w+") as fl:
            fl.write(self.output)


    def load(self, file_name: str | Path):
        """Reads complete docx-file and converts it into markdown"""

        try:
            with zipfile.ZipFile(file_name, 'r') as archive:
                with archive.open("word/document.xml") as fl:
                    self.xml = fl.read().decode("utf-8")

        except FileNotFoundError:
            print(f"[!] File {file_name} could not be found")
            return

        except KeyError:
            print(f"[!] File {file_name} does not seem to be DOCX")
            return

        self.iter = self.tag_pattern.finditer(self.xml)
        self.output = ""

        while self.__next_tag():
            self.__convert_tag()


if __name__ == "__main__":
    doc = DocxDocument("html")

    if len(sys.argv) < 2:
        print("Usage: python docx2md.py <file.docx> [out.md]")
        exit(0)

    file_name = Path(sys.argv[1])
    out_file = Path(file_name if len(sys.argv) != 3 else sys.argv[2])

    doc.load(file_name)
    doc.write(out_file.with_suffix(".md"))



