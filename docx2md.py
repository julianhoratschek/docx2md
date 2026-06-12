from pathlib import Path
from typing import NamedTuple, override
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


class TagConverter:

    def __init__(self, owner: DocxDocument):
        self.owner          : DocxDocument                      = owner
        self.style_stack    : list[StyledSection]               = []
        self.style_mapping  : dict[Styling, tuple[str, str]]    = STYLE_DEFAULT


    @property
    def style(self) -> Styling:
        """Recalculate complete style stack"""
        result = Styling.NoStyle
        for sect in self.style_stack:
            result |= sect.style
        return result


    def process_style_stack(self, tag: Tag) -> bool: 
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
                return False

        return True


    def find_style_tag(self, tag: Tag) -> bool:
        if tag.name in STYLE_TAGS:
            if self.style_stack:
                self.style_stack[-1].style |= STYLE_TAGS[tag.name]
            else:
                self.owner.error("Unexpected styling-tag")
            return True

        return False

    def convert(self, tag: Tag): ...

    def get_result(self) -> str: ...


class TagMdConverter(TagConverter):
    def __init__(self, owner: DocxDocument):
        super().__init__(owner)

        self.in_header: bool    = False
        self.col_count: int     = 0
        self.output   : str     = ""


    @override
    def convert(self, tag: Tag):
        if not self.process_style_stack(tag):
            return

        if self.find_style_tag(tag):
            return

        # Test all other tags
                
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


@dataclass
class HtmlTag:
    name: str
    children: list[HtmlTag | HtmlContent]
    parent: HtmlTag | None


@dataclass
class HtmlContent:
    content: str
    parent: HtmlTag


class TagHtmlConverter(TagConverter):
    def __push_child(self, name: str):
        tag = HtmlTag(name, [], self.html_head)
        self.html_head.children.append(tag)
        self.html_head = tag


    # def __push_sibling(self, name: str):
    #     if (parent := self.html_head.parent) is None:
    #         return
    #     tag = HtmlTag(name, [], parent)
    #     parent.children.append(tag)
        # self.html_head = tag


    def __pop_child(self, name: str):
        if (parent := self.html_head.parent) is None:
            self.owner.error("Cannot ascent over root node")
            return

        if parent.name != name:
            self.owner.error(f"Unexpected closing tag {parent.name}, expected {name}")
            return

        self.html_head = parent


    def __push_content(self, text: str):
        if (parent := self.html_head.parent) is None:
            self.owner.error("Cannot public content under root node")
            return
        content = HtmlContent(text, parent)
        self.html_head.children.append(content)


    def __init__(self, owner: DocxDocument):
        super().__init__(owner)

        self.in_header  : bool  = False
        self.html_tree  : HtmlTag = HtmlTag("body", [], None)
        self.html_head  : HtmlTag = self.html_tree

        self.style_mapping: dict[Styling, tuple[str, str]] = {
            Styling.Bold        : ("<b>", "</b>"),
            Styling.Italic      : ("<i>", "</i>"),
            Styling.Underline   : ("<u>", "</u>"),
            Styling.Striked     : ("<s>", "</s>"),
            Styling.Highlight   : ("<mark>", "</mark>") 
        }


    @override
    def convert(self, tag: Tag):
        if not self.process_style_stack(tag):
            return

        if self.find_style_tag(tag):
            return

        # Test all other tags
                
        match tag.name:
            # Insert paragraph after w:p element
            case "w:p":
                if not tag.closing_state:
                    self.__push_child("p")

                elif self.html_head.name == "li":
                    self.__pop_child("li")
                    # TODO: This is bad
                    self.__pop_child("ul")

                else:
                    self.__pop_child("p")

            # Insert line break
            # case "w:br":
            #     self.__push_sibling("br/")

            # Insert content at beginning of w:t
            case "w:t" if not tag.closing_state:
                self.__push_content(
                    self.style.wrap(
                        self.owner.get_content(), self.style_mapping))

            # Insert list bullets
            case "w:listPr" | "w:numPr" if tag.closing_state:
                if self.html_head.name != "p":
                    self.owner.error("Expected <p> as root for lists")
                    return

                if self.html_head.parent is None:
                    self.owner.error("Cannot insert list at root")
                    return

                # Exchange <p> with <ul> if not inside list yet
                if self.html_head.parent.name != "ul":
                    self.html_head.name = "ul"
                    self.__push_child("li")

                else:
                    self.html_head.name = "li"

            # case "w:ilvl":
            #     try:
            #         lvl = int(tag.attr["w:val"])
            #         return "\t" * lvl
            #     except ValueError:
            #         self.owner.error("Expected numerical indent value for list")
            #     except KeyError:
            #         self.owner.error("Expected w:val in w:ilvl")

            case "w:tbl":
                if tag.closing_state:
                    self.__pop_child("table")
                else:
                    self.__push_child("table")

            case "w:tblHeader":
                self.in_header = True

            case "w:tc":
                s = "h" if self.in_header else "d"
                if tag.closing_state:
                    self.__pop_child(f"t{s}")
                else:
                    self.__push_child(f"t{s}")

            case "w:tr":
                if tag.closing_state:
                    self.__pop_child("tr")
                    self.in_header = False
                else:
                    self.__push_child("tr")

            case _:
                pass


    def print_tag(self, tag: HtmlTag | HtmlContent) -> str:
        match tag:
            case HtmlContent():
                return tag.content

            case HtmlTag():
                if tag.name[-1] == "/":
                    return f"<{tag.name}>"

                return (
                    f"<{tag.name}>" +
                    "".join(self.print_tag(child) for child in tag.children) +
                    f"</{tag.name}>")

    @override
    def get_result(self) -> str:
        return "".join(
            self.print_tag(child) for child in self.html_tree.children)




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


    def __init__(self):
        self.xml            : str                       = ""

        self.tag_pattern    : re.Pattern[str]           = re.compile(
                r"<(?P<closing>/)?" + 
                r"(?P<tag>[\w:_\d]+)" +
                r"(?P<attr>\s+[^/>]*?)?" +
                r"(?P<self_closing>/)?>")
        self.attr_pattern   : re.Pattern[str]           = re.compile(
                r'(?P<name>[\w\d_:]+)="(?P<value>[^"]*)"')

        self.iter           : Iterator[re.Match[str]]   = iter(())
        self.tag            : Tag                       = Tag()

        # self.style_stack    : list[StyledSection]       = []
        self.converter      : TagConverter              = TagMdConverter(self)


    def write(self, file_name: Path | str):
        with Path(file_name).open("w+") as fl:
            fl.write(self.converter.get_result())


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

        while self.__next_tag():
            self.converter.convert(self.tag)


if __name__ == "__main__":
    doc = DocxDocument()

    if len(sys.argv) < 2:
        print("Usage: python docx2md.py <file.docx> [out.md]")
        exit(0)

    file_name = Path(sys.argv[1])
    out_file = Path(file_name if len(sys.argv) != 3 else sys.argv[2])

    doc.load(file_name)
    doc.write(out_file.with_suffix(".md"))



