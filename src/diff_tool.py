"""Text differencing utilities using difflib for deterministic comparison."""
import difflib
from dataclasses import dataclass
from typing import Literal

from .models import PDFExtraction, TextSection


@dataclass
class RawDifference:
    """Represents a raw difference found by difflib before LLM enhancement.
    
    This is the deterministic output from the diff algorithm.
    """
    page_number: int
    section_title: str
    difference_type: Literal["added", "removed", "modified"]
    original_text: str
    new_text: str
    line_number: int  # Line within the document
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "page_number": self.page_number,
            "section_title": self.section_title,
            "difference_type": self.difference_type,
            "original_text": self.original_text,
            "new_text": self.new_text,
            "line_number": self.line_number
        }


class TextDiffer:
    """Handles deterministic text comparison using difflib."""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """Initialize the text differ.
        
        Args:
            similarity_threshold: Threshold for considering lines as "modified" vs "removed+added"
                                 Value between 0 and 1. Higher = more strict.
        """
        self.similarity_threshold = similarity_threshold
    
    def compare_extractions(
        self,
        extraction1: PDFExtraction,
        extraction2: PDFExtraction
    ) -> list[RawDifference]:
        """Compare two PDF extractions and find all differences.
        
        This uses difflib to deterministically find ALL differences between
        the two documents at a line level.
        
        Args:
            extraction1: First PDF extraction
            extraction2: Second PDF extraction
            
        Returns:
            List of RawDifference objects (without LLM context)
        """
        # Build full text documents with line tracking
        doc1_lines, doc1_metadata = self._build_document_with_metadata(extraction1)
        doc2_lines, doc2_metadata = self._build_document_with_metadata(extraction2)
        
        # Use difflib to find all differences
        differ = difflib.Differ()
        diff_result = list(differ.compare(doc1_lines, doc2_lines))
        
        # Parse diff results into structured differences
        differences = self._parse_diff_results(
            diff_result,
            doc1_metadata,
            doc2_metadata
        )
        
        return differences
    
    def _build_document_with_metadata(
        self,
        extraction: PDFExtraction
    ) -> tuple[list[str], dict[int, tuple[int, str]]]:
        """Build a line-by-line document with metadata tracking.
        
        Args:
            extraction: PDF extraction to process
            
        Returns:
            Tuple of (lines, metadata) where:
            - lines: List of text lines
            - metadata: Dict mapping line number to (page_number, section_title)
        """
        lines = []
        metadata = {}
        line_number = 0
        
        for section in extraction.sections:
            # Split section content into lines
            section_lines = section.content.split('\n')
            
            for line in section_lines:
                line = line.strip()
                if line:  # Only include non-empty lines
                    lines.append(line)
                    metadata[line_number] = (section.page_number, section.section_title)
                    line_number += 1
        
        return lines, metadata
    
    def _parse_diff_results(
        self,
        diff_result: list[str],
        doc1_metadata: dict[int, tuple[int, str]],
        doc2_metadata: dict[int, tuple[int, str]]
    ) -> list[RawDifference]:
        """Parse difflib results into RawDifference objects.
        
        Args:
            diff_result: Output from difflib.Differ.compare()
            doc1_metadata: Metadata for document 1
            doc2_metadata: Metadata for document 2
            
        Returns:
            List of RawDifference objects
        """
        differences = []
        doc1_line = 0
        doc2_line = 0
        
        i = 0
        while i < len(diff_result):
            line = diff_result[i]
            
            if line.startswith('  '):  # Unchanged line
                doc1_line += 1
                doc2_line += 1
                i += 1
                
            elif line.startswith('- '):  # Line in doc1 but not doc2
                original_text = line[2:].strip()
                
                # Check if next line is an addition (might be a modification)
                if i + 1 < len(diff_result) and diff_result[i + 1].startswith('+ '):
                    new_text = diff_result[i + 1][2:].strip()
                    
                    # Calculate similarity to determine if it's a modification
                    similarity = difflib.SequenceMatcher(None, original_text, new_text).ratio()
                    
                    if similarity >= self.similarity_threshold:
                        # Treat as modification
                        page_num, section_title = doc1_metadata.get(doc1_line, (0, "Unknown"))
                        differences.append(RawDifference(
                            page_number=page_num,
                            section_title=section_title,
                            difference_type="modified",
                            original_text=original_text,
                            new_text=new_text,
                            line_number=doc1_line
                        ))
                        doc1_line += 1
                        doc2_line += 1
                        i += 2  # Skip both lines
                        continue
                
                # Otherwise, it's a removal
                page_num, section_title = doc1_metadata.get(doc1_line, (0, "Unknown"))
                differences.append(RawDifference(
                    page_number=page_num,
                    section_title=section_title,
                    difference_type="removed",
                    original_text=original_text,
                    new_text="",
                    line_number=doc1_line
                ))
                doc1_line += 1
                i += 1
                
            elif line.startswith('+ '):  # Line in doc2 but not doc1
                new_text = line[2:].strip()
                page_num, section_title = doc2_metadata.get(doc2_line, (0, "Unknown"))
                
                differences.append(RawDifference(
                    page_number=page_num,
                    section_title=section_title,
                    difference_type="added",
                    original_text="",
                    new_text=new_text,
                    line_number=doc2_line
                ))
                doc2_line += 1
                i += 1
                
            else:  # Diff marker line
                i += 1
        
        return differences
    
    def group_related_differences(
        self,
        differences: list[RawDifference],
        max_distance: int = 3
    ) -> list[list[RawDifference]]:
        """Group differences that are close together (for batch LLM processing).
        
        Args:
            differences: List of raw differences
            max_distance: Maximum line distance to consider differences as related
            
        Returns:
            List of difference groups
        """
        if not differences:
            return []
        
        # Sort by line number
        sorted_diffs = sorted(differences, key=lambda d: d.line_number)
        
        groups = []
        current_group = [sorted_diffs[0]]
        
        for diff in sorted_diffs[1:]:
            # If this diff is close to the last one in current group, add it
            if diff.line_number - current_group[-1].line_number <= max_distance:
                current_group.append(diff)
            else:
                # Start a new group
                groups.append(current_group)
                current_group = [diff]
        
        # Don't forget the last group
        if current_group:
            groups.append(current_group)
        
        return groups
