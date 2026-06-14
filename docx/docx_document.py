from collections.abc import Iterator
from pathlib import Path

import re
import zipfile

from .tag import Tag, ClosingState
from .converters import TagConverter, TagMdConverter


TAG_PATTERN : re.Pattern[str] = re.compile(
    r"<(?P<closing>/)?" + 
    r"(?P<tag>[\w:_\d]+)" +
    r"(?P<attr>\s+[^/>]*?)?" +
    r"(?P<self_closing>/)?>")

ATTR_PATTERN: re.Pattern[str] = re.compile(
    r'(?P<name>[\w\d_:]+)="(?P<value>[^"]*)"')


class DocxDocument:
    """
    Loads ooxml content from a provided docx file and saves it according to
    a provided converter as markdown or html.

    :ivar __xml    : Complete xml read from docx
    :ivar __iter   : Regex Match iterator for tags over read ooxml
    :ivar tag      : Tag representation of current Regex Match
    :ivar converter: TagConverter instance to use on read tags
    """

    def __init__(self, css_file: Path | None = None):
        self.__xml    : str                     = ""
        self.__iter   : Iterator[re.Match[str]] = iter(())
        self.tag      : Tag                     = Tag()
        self.converter: TagConverter            = TagMdConverter(self)
        self.css_path : Path                    = css_file or Path(__file__).parent.parent / "style.css"


    def error(self, msg: str):
        """Prints `msg` as an error, providing the current location in xml"""
        print(f"[!] {self.tag.start}: {msg}")


    def next_tag(self) -> bool:
        """Increments the internal iterator and reads `self.tag`"""

        try:
            tag_match = next(self.__iter)
        except StopIteration:
            return False

        # Read closing state

        closing_state = ClosingState.Opening
        if tag_match["closing"]:
            closing_state |= ClosingState.Closing
        if tag_match["self_closing"]:
            closing_state |= ClosingState.SelfClosing

        # Read Attribute list

        attr_list: dict[str, str] = {
            m["name"]: m["value"]
            for m in ATTR_PATTERN.finditer(tag_match["attr"])
        } if tag_match["attr"] else {}

        # Create tag

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


    def write(self, file_name: Path | str):
        """Save converter-output to a file"""

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

        self.__iter = TAG_PATTERN.finditer(self.__xml)

        while self.next_tag():
            self.converter.convert(self.tag)
