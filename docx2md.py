from pathlib import Path
from typing import NamedTuple
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


class Styling(IntFlag):
    NoStyle     = 0b00000
    Italic      = 0b00001
    Bold        = 0b00010
    Underline   = 0b00100
    Striked     = 0b01000
    Highlight   = 0b10000


@dataclass
class StyledSection:
    tag     : Tag
    style   : Styling   = Styling.NoStyle


class DocxDocument:
    def __init__(self):
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
        self.tag_match      : re.Match[str]             = None
        self.tag            : Tag                       = Tag()

        self.style_stack    : list[StyledSection]       = []


    @property
    def style(self) -> Styling:
        """Recalculate complete style stack"""

        result = Styling.NoStyle

        for sect in self.style_stack:
            result |= sect.style

        return result
    

    @property
    def style_tag(self) -> Tag:
        return self.style_stack[-1].tag


    def push_style(self, style: Styling):
        self.style_stack[-1].style |= style


    def write(self, file_name: Path | str):
        with Path(file_name).open("w+") as fl:
            fl.write(self.output)


    def get_content(self) -> str:
        """Get complete text between <w:t> and </w:t>"""

        begin = self.tag_match.end()
        if not self.next_tag():
            print(f"[!] {begin}: Unexpected End Of File, expected </w:t>")
            return ""

        if self.tag.name != "w:t":
            print(f"[!] {begin}: Unexpected closing Tag, expected </w:t>")
            return ""

        if not self.tag.closing_state:
            print(f"[!] {begin}: Unexpected opening tag <w:t>")
            return ""

        end = self.tag_match.start()
        return self.xml[begin:end]

    
    def apply_style(self, text: str) -> str:
        """Change `text` to represent current styling in markdown"""

        style = self.style

        if Styling.Bold in style:
            text = f"**{text}**"

        if Styling.Italic in style:
            text = f"*{text}*"

        if Styling.Underline in style:
            text = f"<u>{text}</u>"

        if Styling.Striked in style:
            text = f"~~{text}~~"

        if Styling.Highlight in style:
            text = f"=={text}=="

        return text


    def convert_tag(self):
        """Converts the current `self.tag` into markdown and saves it into
        `self.output`. <w:t> tags content will be read completely."""

        # Test for elements that can contain styling hints
        if self.tag.name in ("w:p", "w:r"):

            # Opening tag
            if not self.tag.closing_state:
                self.style_stack.append(StyledSection(self.tag))

            # Closing tag
            elif self.style_stack and self.tag.name == self.style_tag.name:
                self.style_stack.pop()

            else:
                err_msg = f"[!] {self.tag_match.start()}: Unexpected closing tag {self.tag.name}"
                if self.style_stack:
                    err_msg += f", expected {self.style_tag.name}"
                print(err_msg)
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
                print(f"[!] {self.tag_match.start()}: Unexpected styling-tag")
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
                self.output += self.apply_style(self.get_content())

            # Insert list bullets
            # TODO: Numerical lists
            case "w:listPr" | "w:numPr" if self.tag.closing_state:
                self.output += "- "

            case "w:ilvl":
                try:
                    lvl = int(self.tag.attr["w:val"])
                    self.output += "\t" * lvl
                except ValueError:
                    print("[!] Expected numerical indent value for list")
                except KeyError:
                    print("[!] Expected w:val in w:ilvl")

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


    def get_tag(self):
        """Reads the current `self.tag_match` into `self.tag`"""

        closing_state = ClosingState.Opening

        if self.tag_match["closing"]:
            closing_state |= ClosingState.Closing
        if self.tag_match["self_closing"]:
            closing_state |= ClosingState.SelfClosing

        attr_list: dict[str, str] = {
            m["name"]: m["value"]
            for m in self.attr_pattern.finditer(self.tag_match["attr"])
        } if self.tag_match["attr"] else {}

        self.tag = Tag(
            self.tag_match["tag"],
            attr_list,
            closing_state)


    def next_tag(self) -> bool:
        """Increments internal tag-iterator. Sets `self.tag_match` to current
        tag and reads it into `self.tag`"""

        try:
            self.tag_match = next(self.iter)
        except StopIteration:
            return False

        self.get_tag()
        return True


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

        while self.next_tag():
            self.convert_tag()


if __name__ == "__main__":
    doc = DocxDocument()

    if len(sys.argv) < 2:
        print("Usage: python docx2md.py <file.docx> [out.md]")
        exit(0)

    file_name = Path(sys.argv[1])
    out_file = Path(file_name if len(sys.argv) != 3 else sys.argv[2])

    doc.load(file_name)
    doc.write(out_file.with_suffix(".md"))



