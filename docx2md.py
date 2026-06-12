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
        self.style          : Styling                   = Styling.NoStyle


    def push_style(self, style: Styling):
        self.style_stack[-1].style |= style
        self.style |= style


    def pop_styled_section(self):
        # TODO: This is not correct
        #   Either work with counters or re-calculate style stack

        # Remove Section
        self.style_stack.pop()
        self.style = Styling.NoStyle

        for sect in self.style_stack:
            self.style |= sect .style


    def write(self, file_name: Path | str):
        with Path(file_name).open("w+") as fl:
            fl.write(self.output)


    def get_content(self) -> str:
        begin = self.tag_match.end()
        if not self.next_tag():
            print("[!] Unexpected End Of File, expected </w:t>")
            return ""

        if self.tag.name != "w:t":
            print("[!] Unexpected closing Tag, expected </w:t>")
            return ""

        if not self.tag.closing_state:
            print("[!] Unexpected opening tag <w:t>")
            return ""

        end = self.tag_match.start()
        return self.xml[begin:end]

    
    def apply_style(self, text: str) -> str:
        if Styling.Bold in self.style:
            text = f"**{text}**"
        if Styling.Italic in self.style:
            text = f"*{text}*"
        if Styling.Underline in self.style:
            text = f"<u>{text}</u>"
        if Styling.Striked in self.style:
            text = f"~~{text}~~"
        if Styling.Highlight in self.style:
            text = f"=={text}=="
        return text


    def convert_tag(self):
        if self.tag.name in ("w:p", "w:r"):
            if self.tag.closing_state:
                if self.tag.name == self.style_stack[-1].tag.name:
                    self.pop_styled_section()
                else:
                    print(f"[!] Unexpected closing tag {self.tag.name}, expected {self.style_stack[-1].tag.name}")
                    return
            else:
                self.style_stack.append(StyledSection(self.tag))

        styles = {
            "w:b": Styling.Bold,
            "w:i": Styling.Italic,
            "w:u": Styling.Underline,
            "w:strike": Styling.Striked,
            "w:highlight": Styling.Highlight
        }

        if self.tag.name in styles:
            self.push_style(styles[self.tag.name])
            return
                
        match self.tag.name:
            case "w:p" if self.tag.closing_state:
                self.output += "\n\n"

            case "w:br":
                self.output += "\\\n"

            case "w:t" if not self.tag.closing_state:
                self.output += self.apply_style(self.get_content())

            # TODO: Numerical lists
            case "w:listPr" | "w:numPr" if self.tag.closing_state:
                self.output += "- "

            case "w:ilvl":
                try:
                    lvl = int(self.tag.attr["w:val"])
                    self.output += "\t" * lvl
                # TODO: handle
                except ValueError:
                    print("[!] Expected numerical indent value for list")
                except KeyError:
                    print("[!] Expected w:val in w:ilvl")

            # TODO: Table as html
            case "w:tblHeader":
                self.in_header = True
                self.col_count = 0

            # TODO: p is no newline
            case "w:tc":
                self.output += "|"
                if self.in_header and self.tag.closing_state:
                    self.col_count += 1

            case "w:tr" if self.tag.closing_state:
                self.output += "\n"
                if self.in_header:
                    self.in_header = False
                    self.output += "|" + "---|" * self.col_count

            case _:
                pass


    def get_tag(self):
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

        # print(f"{'/' if self.tag.closing_state else ' '}{self.tag.name}")


    def next_tag(self) -> bool:
        try:
            self.tag_match = next(self.iter)
        except StopIteration:
            return False

        self.get_tag()
        return True


    def load(self, file_name: str | Path):
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

        # with Path(file_name).open("r") as fl:
        #     self.xml = "".join(fl.readlines()[2:])

        self.iter = self.tag_pattern.finditer(self.xml)

        while self.next_tag():
            self.convert_tag()


if __name__ == "__main__":
    doc = DocxDocument()

    if len(sys.argv) < 2:
        print("Usage: docx2md <file.docx> [out.md]")
        exit(0)

    file_name = Path(sys.argv[1])
    out_file = Path(file_name if len(sys.argv) != 3 else sys.argv[2])

    doc.load(file_name)
    doc.write(out_file.with_suffix(".md"))



