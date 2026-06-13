from typing import override
from dataclasses import dataclass

from ..tag import Tag
from ..style import Styling, STYLE_TAGS
from .converter import DocxProtocol, TagConverter


@dataclass
class HtmlTag:
    name    : str
    children: list[HtmlTag | HtmlContent]
    parent  : HtmlTag | None


@dataclass
class HtmlContent:
    content: str
    parent : HtmlTag


class TagHtmlConverter(TagConverter):
    def __push_child(self, name: str):
        tag = HtmlTag(name, [], self.__html_head)

        self.__html_head.children.append(tag)
        self.__html_head = tag


    def __pop_child(self, name: str):
        if (parent := self.__html_head.parent) is None:
            return self.owner.error("Cannot ascend over root node")

        if self.__html_head.name != name:
            return self.owner.error(f"Unexpected closing tag {self.__html_head.name}, expected {name}")

        self.__html_head = parent


    def __push_content(self, text: str):
        if (parent := self.__html_head.parent) is None:
            return self.owner.error("Cannot public content under root node")

        content = HtmlContent(text, parent)
        self.__html_head.children.append(content)


    def __get_list_index(self) -> int:
        """
        Returns the indentation index of the current list element. If the current
        tag is not a list element, returns 0.
        """

        if not self.owner.next_tag() \
           or self.owner.tag.name != "w:pPr":
            return 0

        list_idx = 0
        while self.owner.next_tag():
            tag = self.owner.tag

            # Still process style tags
            if tag.name in STYLE_TAGS:
                self.convert_style_tag(tag)
                continue

            match tag.name:
                case "w:pPr":
                    break

                case "w:numPr":
                    list_idx = list_idx or 1

                case "w:ilvl":
                    try:
                        list_idx = int(tag.attr["w:val"]) + 1
                    except ValueError:
                        self.owner.error("Expected numerical indent value for list")
                    except KeyError:
                        self.owner.error("Expected w:val in w:ilvl")

        return list_idx


    def __init__(self, owner: DocxProtocol):
        super().__init__(owner)

        self.__in_header  : bool    = False
        self.__list_idx   : int     = 0
        self.__html_tree  : HtmlTag = HtmlTag("body", [], None)
        self.__html_head  : HtmlTag = self.__html_tree

        self.extension    : str     = ".html"
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

        if tag.name in STYLE_TAGS:
            return self.convert_style_tag(tag)

        match tag.name:
            # Insert paragraph or unordered list
            case "w:p":
                if not tag.closing_state:
                    if (list_idx := self.__get_list_index()):
                        while self.__list_idx < list_idx:
                            self.__push_child("ul")
                            self.__list_idx += 1

                        while self.__list_idx > list_idx:
                            self.__pop_child("ul")
                            self.__list_idx -= 1

                        self.__push_child("li")

                    else:
                        if self.__list_idx:
                            while self.__list_idx:
                                self.__pop_child("ul")
                                self.__list_idx -= 1
                        self.__push_child("p")

                elif self.__list_idx:
                    self.__pop_child("li")

                else:
                    self.__pop_child("p")

            # Insert content at beginning of w:t
            case "w:t" if not tag.closing_state:
                self.__push_content(
                    self.style.wrap(
                        self.owner.get_content(), self.style_mapping))

            # TODO: ul levels


            case "w:tbl":
                if tag.closing_state:
                    self.__pop_child("table")
                else:
                    self.__push_child("table")

            case "w:tblHeader":
                self.__in_header = True

            case "w:tc":
                s = "th" if self.__in_header else "td"
                if tag.closing_state:
                    self.__pop_child(s)
                else:
                    self.__push_child(s)

            case "w:tr":
                if tag.closing_state:
                    self.__pop_child("tr")
                    self.__in_header = False
                else:
                    self.__push_child("tr")

            case _:
                pass


    def __print_tag(self, tag: HtmlTag | HtmlContent) -> str:
        match tag:
            case HtmlContent():
                return tag.content

            case HtmlTag():
                if tag.name[-1] == "/":
                    return f"<{tag.name}>"

                return f"""
        <{tag.name}>
            {"".join(self.__print_tag(child) for child in tag.children)}
        </{tag.name}>"""

    @override
    def get_result(self) -> str:
        return f"""
<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" href="{self.owner.css_path.absolute()}" />
    </head>

    <body>
        <div class="page">
            {"".join(self.__print_tag(child)
            for child in self.__html_tree.children)}
        </div>
    </body>
</html>
"""
