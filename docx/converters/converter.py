from typing import Protocol

from ..style import StyledSection, Styling, STYLE_DEFAULT, STYLE_TAGS
from ..tag import Tag

class DocxProtocol(Protocol):
    def error(self, msg: str): ...
    def get_content(self) -> str: ...
    def next_tag(self) -> bool: ...

    @property
    def tag(self) -> Tag: ...


class TagConverter:

    def __init__(self, owner: DocxProtocol):
        self.owner          : DocxProtocol = owner
        self.style_stack    : list[StyledSection]               = []
        self.style_mapping  : dict[Styling, tuple[str, str]]    = STYLE_DEFAULT
        self.extension      : str                               = ".md"


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


    def convert_style_tag(self, tag: Tag):
        # if tag.name in STYLE_TAGS:
        if self.style_stack:
            self.style_stack[-1].style |= STYLE_TAGS[tag.name]
        else:
            self.owner.error("Unexpected styling-tag")
        #     return True
        #
        # return False

    def convert(self, tag: Tag): ...

    def get_result(self) -> str: ...




