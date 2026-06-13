from typing import Protocol
from pathlib import Path

from ..style import StyledSection, Styling, STYLE_DEFAULT, STYLE_TAGS
from ..tag import Tag


class DocxProtocol(Protocol):
    def error(self, msg: str): ...
    def get_content(self) -> str: ...
    def next_tag(self) -> bool: ...

    @property
    def tag(self) -> Tag: ...

    @property
    def css_path(self) -> Path: ...


class TagConverter:
    """
    Base class for docx-converters.

    :ivar owner        :    DocxDocument instance owning the converter
    :ivar style_stack  :    StyledSections influencing the current style
    :ivar style_mapping:    Mapping used for Styling.wrap
    :ivar extension    :    File Extension for output format
    """

    def __init__(self, owner: DocxProtocol):
        self.owner        : DocxProtocol                   = owner
        self.style_stack  : list[StyledSection]            = []
        self.style_mapping: dict[Styling, tuple[str, str]] = STYLE_DEFAULT
        self.extension    : str                            = ".md"


    @property
    def style(self) -> Styling:
        """
        Returns the complete StyledSection Stack as Styling
        """
        result = Styling.NoStyle
        for sect in self.style_stack:
            result |= sect.style
        return result


    def process_style_stack(self, tag: Tag) -> bool: 
        """
        Pushes or pops StyledSections onto `self.style_stack` if a
        styleable section is encountered ("w:p" or "w:r").
        
        :param tag: Current tag
        :returns  : False if closing tag does not match opening styleable tag
        """
        if tag.name not in ("w:p", "w:r"):
            return True

        # Opening tag
        if not tag.closing_state:
            self.style_stack.append(StyledSection(tag))

        # Closing tag
        elif self.style_stack and tag.name == self.style_stack[-1].tag.name:
            self.style_stack.pop()

        # Not matching closing tag
        else:
            err_msg = f"Unexpected closing tag {tag.name}"
            if self.style_stack:
                err_msg += f", expected {self.style_stack[-1].tag.name}"
            self.owner.error(err_msg)
            return False

        return True


    def convert_style_tag(self, tag: Tag):
        """
        Adds a style tag - if encountered - to the current StyledSection.
        This is necessary, as ooxml predefines styles in w:pPr or w:rPr and
        uses those styles much later when displaying text in w:t.

        :param tag: Current tag
        """
        if not self.style_stack:
            return self.owner.error("Unexpected styling-tag")

        self.style_stack[-1].style |= STYLE_TAGS[tag.name]


    def convert(self, tag: Tag):
        """Override this to convert encountered tags to your desired format"""
        ...
        

    def get_result(self) -> str:
        """Override this to return the end result of the converted text"""
        ...


