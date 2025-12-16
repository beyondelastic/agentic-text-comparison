"""PDF extraction utilities using multiple strategies."""
import json
from pathlib import Path
from typing import Any

import pdfplumber
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from .config import AzureDocumentIntelligenceConfig
from .models import PDFExtraction, TextSection


class PDFExtractor:
    """Handles PDF extraction using various strategies."""
    
    def __init__(self, doc_intel_config: AzureDocumentIntelligenceConfig | None = None):
        """Initialize PDF extractor.
        
        Args:
            doc_intel_config: Azure Document Intelligence configuration (optional)
        """
        self.doc_intel_config = doc_intel_config
        self.doc_intel_client = None
        
        if doc_intel_config:
            self.doc_intel_client = DocumentIntelligenceClient(
                endpoint=doc_intel_config.endpoint,
                credential=AzureKeyCredential(doc_intel_config.api_key)
            )
    
    def extract_with_pdfplumber(self, pdf_path: Path) -> PDFExtraction:
        """Extract text from PDF using pdfplumber (simple, fast, local).
        
        This method extracts text page by page and attempts to identify sections
        based on formatting patterns.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFExtraction: Structured extraction result
        """
        sections = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text from the page
                text = page.extract_text()
                
                if not text:
                    continue
                
                # Split into paragraphs (simple heuristic)
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                
                # Create sections from paragraphs
                for order, paragraph in enumerate(paragraphs, start=1):
                    # Try to detect if first line is a heading (all caps, short, ends with specific chars)
                    lines = paragraph.split('\n')
                    if len(lines) > 1 and len(lines[0]) < 100:
                        section_title = lines[0].strip()
                        content = '\n'.join(lines[1:]).strip()
                    else:
                        section_title = f"Section {order}"
                        content = paragraph
                    
                    if content:  # Only add non-empty sections
                        sections.append(TextSection(
                            page_number=page_num,
                            section_title=section_title,
                            content=content,
                            order=order
                        ))
        
        return PDFExtraction(
            filename=pdf_path.name,
            total_pages=total_pages,
            sections=sections
        )
    
    def extract_with_document_intelligence(self, pdf_path: Path) -> PDFExtraction:
        """Extract text from PDF using Azure Document Intelligence (advanced).
        
        This method provides better structure recognition, table extraction,
        and section identification.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFExtraction: Structured extraction result
            
        Raises:
            ValueError: If Document Intelligence is not configured
        """
        if not self.doc_intel_client:
            raise ValueError("Azure Document Intelligence is not configured")
        
        sections = []
        
        # Read the PDF file
        with open(pdf_path, "rb") as f:
            poller = self.doc_intel_client.begin_analyze_document(
                "prebuilt-layout",
                analyze_request=f,
                content_type="application/pdf"
            )
        
        result = poller.result()
        
        # Extract sections from paragraphs
        order = 1
        for paragraph in result.paragraphs:
            page_num = paragraph.bounding_regions[0].page_number if paragraph.bounding_regions else 1
            
            # Determine if this is a heading based on role or formatting
            is_heading = paragraph.role in ["title", "sectionHeading"] if hasattr(paragraph, 'role') else False
            
            section_title = paragraph.content if is_heading else f"Section {order}"
            content = paragraph.content if not is_heading else ""
            
            if content:
                sections.append(TextSection(
                    page_number=page_num,
                    section_title=section_title,
                    content=content,
                    order=order
                ))
                order += 1
        
        return PDFExtraction(
            filename=pdf_path.name,
            total_pages=len(result.pages),
            sections=sections
        )
    
    def extract(self, pdf_path: Path, use_document_intelligence: bool = False) -> PDFExtraction:
        """Extract text from PDF using the best available method.
        
        Args:
            pdf_path: Path to the PDF file
            use_document_intelligence: Force use of Azure Document Intelligence
            
        Returns:
            PDFExtraction: Structured extraction result
        """
        if use_document_intelligence and self.doc_intel_client:
            print(f"Extracting {pdf_path.name} using Azure Document Intelligence...")
            return self.extract_with_document_intelligence(pdf_path)
        else:
            print(f"Extracting {pdf_path.name} using pdfplumber...")
            return self.extract_with_pdfplumber(pdf_path)
    
    def save_extraction(self, extraction: PDFExtraction, output_path: Path) -> None:
        """Save extraction result to JSON file.
        
        Args:
            extraction: The extraction result to save
            output_path: Path where to save the JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extraction.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"Saved extraction to {output_path}")
