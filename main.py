from _typeshed import OpenBinaryModeReading
from pathlib import Path
from typing import NamedTuple
from enum import IntFlag
import re


class ClosingState(IntFlag):
    Opening     = 0b00
    Closing     = 0b01
    SelfClosing = 0b10


class Tag(NamedTuple):
    name: str
    attr: str
    closing_state: ClosingState


class DocxDocument:
    def __init__(self):
        self.xml: str = ""
        self.idx: int = 0

        self.tag_pattern = re.compile(r"(?P<closing>/)(?P<tag>[\w:_\d]+)(?P<attr>\s+[^/>]*?)?(?P<self_closing>/)?")
        self.text_pattern = re.compile(r"(?P<text>.*?)</w:t>")

        self.output: str = ""
        self.in_header: bool = False
        self.col_count: int = 0


    def get_content(self) -> str:
        if not (m := self.text_pattern.match(self.xml, self.idx)):
            # TODO: handle this
            return ""
        return m["text"]


    def convert_tag(self, tag: Tag):
        match tag.name:
            case "w:p" if tag.closing_state:
                self.output += "\n"

            case "w:t" if not tag.closing_state:
                self.output += self.get_content()

            # TODO: Numerical lists
            case "w:listPr" if not tag.closing_state:
                self.output += "  - "

            # TODO: Table as html
            case "w:tblHeader":
                self.in_header = True
                self.col_count = 0

            # TODO: p is no newline
            case "w:tc":
                self.output += "|"
                if self.in_header and tag.closing_state:
                    self.col_count += 1

            case "w:tr" if tag.closing_state:
                self.output += "\n"
                if self.in_header:
                    self.in_header = False
                    self.output += "|" + "---|" * self.col_count


    def process_tag(self):
        begin = self.idx + 1
        end = begin
        # TODO: Escpaed chars
        while end < len(self.xml) and self.xml[end] != '>':
            end += 1

        tag_line = self.xml[begin:end]
        if not (tag_match := self.tag_pattern.match(tag_line)):
            return

        closing_state = ClosingState.Opening

        if tag_match["closing"]:
            closing_state |= ClosingState.Closing
        if tag_match["self_closing"]:
            closing_state |= ClosingState.SelfClosing

        tag = Tag(
            tag_match["tag"],
            tag_match["attr"],
            closing_state)

        self.convert_tag(tag)
        self.idx = end


    def load(self, file_name: str | Path):
        with Path(file_name).open("r") as fl:
            self.xml = fl.read()

        self.idx = 0
        while self.idx < len(self.xml):
            if self.xml[self.idx] == '<':
                self.process_tag()



if __name__ == "__main__":
    pass
