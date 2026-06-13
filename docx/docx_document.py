from collections.abc import Iterator
from pathlib import Path

import re
import zipfile

from .tag import Tag, ClosingState
from .converters import TagConverter, TagMdConverter


class DocxDocument:
    def error(self, msg: str):
        print(f"[!] {self.tag.start}: {msg}")

    def next_tag(self) -> bool:
        """Increments the internal iterator and reads `self.tag`"""

        try:
            tag_match = next(self.__iter)
        except StopIteration:
            return False

        closing_state = ClosingState.Opening
        if tag_match["closing"]:
            closing_state |= ClosingState.Closing
        if tag_match["self_closing"]:
            closing_state |= ClosingState.SelfClosing

        attr_list: dict[str, str] = {
            m["name"]: m["value"]
            for m in self.__attr_pattern.finditer(tag_match["attr"])
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
        if not self.next_tag():
            self.error("Unexpected End Of File, expected </w:t>")
            return ""

        if self.tag.name != "w:t":
            self.error("Unexpected closing Tag, expected </w:t>")
            return ""

        if not self.tag.closing_state:
            self.error("Unexpected opening tag <w:t>")
            return ""

        end = self.tag.start
        return self.__xml[begin:end]


    def __init__(self):
        self.__xml          : str                       = ""

        self.__tag_pattern  : re.Pattern[str]           = re.compile(
                r"<(?P<closing>/)?" + 
                r"(?P<tag>[\w:_\d]+)" +
                r"(?P<attr>\s+[^/>]*?)?" +
                r"(?P<self_closing>/)?>")
        self.__attr_pattern : re.Pattern[str]           = re.compile(
                r'(?P<name>[\w\d_:]+)="(?P<value>[^"]*)"')

        self.__iter         : Iterator[re.Match[str]]   = iter(())
        self.tag            : Tag                       = Tag()

        # self.style_stack    : list[StyledSection]       = []
        self.converter      : TagConverter              = TagMdConverter(self)


    def write(self, file_name: Path | str):
        with Path(file_name)\
                .with_suffix(self.converter.extension)\
                .open("w+") as fl:
            fl.write(self.converter.get_result())


    def load(self, file_name: str | Path):
        """Reads complete docx-file and converts it into markdown"""

        try:
            with zipfile.ZipFile(file_name, 'r') as archive:
                with archive.open("word/document.xml") as fl:
                    self.__xml = fl.read().decode("utf-8")

        except FileNotFoundError:
            print(f"[!] File {file_name} could not be found")
            return

        except KeyError:
            print(f"[!] File {file_name} does not seem to be DOCX")
            return

        self.__iter = self.__tag_pattern.finditer(self.__xml)

        while self.next_tag():
            self.converter.convert(self.tag)
