"""Data models for the PDF comparison workflow."""
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TextSection:
    """Represents a section of text from a PDF."""
    page_number: int
    section_title: str
    content: str
    order: int  # Order within the page
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_number": self.page_number,
            "section_title": self.section_title,
            "content": self.content,
            "order": self.order
        }


@dataclass
class PDFExtraction:
    """Represents the complete extraction from a PDF document."""
    filename: str
    total_pages: int
    sections: list[TextSection] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "total_pages": self.total_pages,
            "sections": [section.to_dict() for section in self.sections]
        }


@dataclass
class TextDifference:
    """Represents a difference found between two PDF documents."""
    page_number: int
    section: str
    difference_type: Literal["added", "removed", "modified"]
    original_text: str
    new_text: str
    context: str = ""  # Surrounding text for context
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV/JSON export."""
        return {
            "page_number": self.page_number,
            "section": self.section,
            "difference_type": self.difference_type,
            "original_text": self.original_text,
            "new_text": self.new_text,
            "context": self.context
        }


@dataclass
class ComparisonResult:
    """Complete comparison result between two PDFs."""
    pdf1_name: str
    pdf2_name: str
    differences: list[TextDifference] = field(default_factory=list)
    total_differences: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pdf1_name": self.pdf1_name,
            "pdf2_name": self.pdf2_name,
            "total_differences": self.total_differences,
            "differences": [diff.to_dict() for diff in self.differences]
        }
