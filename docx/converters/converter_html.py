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
        """Add a child node to `html_head` and set head to child"""
        tag = HtmlTag(name, [], self.__html_head)

        self.__html_head.children.append(tag)
        self.__html_head = tag


    def __pop_child(self, name: str):
        """Keeps child node! Sets `html_head` to parent"""
        if (parent := self.__html_head.parent) is None:
            return self.owner.error("Cannot ascend over root node")

        if self.__html_head.name != name:
            return self.owner.error(f"Unexpected closing tag {self.__html_head.name}, expected {name}")

        self.__html_head = parent


    # def __remove_current(self, name: str):
    #     """Removes `html_head` from current tree and sets `html_head` to parent"""
    #     self.__pop_child(name)
    #     self.__html_head.children.pop()


    def __push_content(self, text: str):
        """Pushes text as child to `html_head`, keeps `html_head` at current node"""
        if (parent := self.__html_head.parent) is None:
            return self.owner.error("Cannot public content under root node")

        content = HtmlContent(text, parent)
        self.__html_head.children.append(content)


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
            # Opens a paragraph, could be changed after processing w:pPr
            case "w:p" if not tag.closing_state:
                # Each w:p should have a pPr, where we insert the correct
                # paragraph type (p, li, h)
                # self.__push_child("p")
                pass

            # Closes lists, paragraphs or headings
            case "w:p" if tag.closing_state:
                name = self.__html_head.name
                if name in ("li", "p") or name[0] == "h":
                    self.__pop_child(name)
                else:
                    self.owner.error("Unexpected w:p closing tag")

            # Read p properties and change last p if necessary
            case "w:pPr" if not tag.closing_state:
                # We did not insert a paragraph when encountering w:p
                # self.__remove_current("p")
                ppr = self.process_ppr()

                # Current paragraph is a list element
                if ppr.list_level:
                    while self.__list_idx < ppr.list_level:
                        self.__push_child("ul")
                        self.__list_idx += 1

                    while self.__list_idx > ppr.list_level:
                        self.__pop_child("ul")
                        self.__list_idx -= 1

                    self.__push_child("li")
                    return

                # Current paragraph is no list element (anymore)
                while self.__list_idx:
                    self.__pop_child("ul")
                    self.__list_idx -= 1

                # Current paragraph is heading
                if ppr.heading_level:
                    self.__push_child(f"h{ppr.heading_level % 6}")
                    return
                
                # Nothing changed: current paragraph stays paragraph
                self.__push_child("p")

            # Insert content at beginning of w:t
            case "w:t" if not tag.closing_state:
                self.__push_content(
                    self.style.wrap(
                        self.owner.get_content(), self.style_mapping))

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
        """ Tail-recursive function to print all tags and their children """
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
