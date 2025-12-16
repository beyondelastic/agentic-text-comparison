"""AI Agents for PDF extraction and comparison using Microsoft Agent Framework."""
import json
from pathlib import Path
from typing import Any

from agent_framework import (
    ChatAgent,
    ChatMessage,
    Executor,
    Role,
    WorkflowContext,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential
from typing_extensions import Never

from .config import AzureOpenAIConfig
from .models import ComparisonResult, PDFExtraction, TextDifference
from .pdf_extractor import PDFExtractor


class PDFExtractionAgent(Executor):
    """Agent responsible for extracting and structuring content from PDF files.
    
    This agent uses PDF extraction tools and then organizes the content into
    a structured JSON format suitable for comparison.
    """
    
    def __init__(
        self,
        pdf_extractor: PDFExtractor,
        chat_client: AzureOpenAIChatClient,
        id: str = "pdf_extraction_agent"
    ):
        """Initialize the PDF extraction agent.
        
        Args:
            pdf_extractor: PDF extraction utility
            chat_client: Azure OpenAI chat client
            id: Executor ID
        """
        self.pdf_extractor = pdf_extractor
        self.agent = chat_client.create_agent(
            instructions="""You are an expert PDF content analyzer specialized in pharmaceutical documentation.
            
Your task is to analyze extracted PDF content and organize it into structured sections.

Key responsibilities:
1. Review the extracted text sections from the PDF
2. Identify and label meaningful sections (e.g., "Introduction", "Dosage", "Side Effects", etc.)
3. Ensure content is properly organized by page and section order
4. Preserve all important information without summarization

Output the analysis as a well-structured JSON format that maintains:
- Page numbers
- Section titles
- Complete text content
- Proper ordering

Be thorough and accurate - this data will be used for detailed comparison."""
        )
        super().__init__(id=id)
    
    @handler
    async def extract_pdfs(
        self,
        pdf_paths: tuple[Path, Path],
        ctx: WorkflowContext[tuple[PDFExtraction, PDFExtraction]]
    ) -> None:
        """Extract content from two PDF files.
        
        Args:
            pdf_paths: Tuple containing paths to two PDF files
            ctx: Workflow context for sending results to next agent
        """
        pdf1_path, pdf2_path = pdf_paths
        
        # Extract both PDFs using the extraction tool
        print(f"\n{'='*60}")
        print("STEP 1: Extracting PDF Content")
        print(f"{'='*60}")
        
        extraction1 = self.pdf_extractor.extract(pdf1_path)
        print(f"✓ Extracted {len(extraction1.sections)} sections from {extraction1.filename}")
        
        extraction2 = self.pdf_extractor.extract(pdf2_path)
        print(f"✓ Extracted {len(extraction2.sections)} sections from {extraction2.filename}")
        
        # Optionally enhance the extractions with AI analysis
        # The agent can reorganize or improve section labeling if needed
        print("\n✓ PDF extraction completed successfully")
        
        # Send both extractions to the comparison agent
        await ctx.send_message((extraction1, extraction2))


class PDFComparisonAgent(Executor):
    """Agent responsible for comparing two PDF extractions and finding differences.
    
    This agent performs intelligent, word-level comparison of the extracted content
    and identifies all differences between the two documents.
    """
    
    def __init__(
        self,
        chat_client: AzureOpenAIChatClient,
        id: str = "pdf_comparison_agent"
    ):
        """Initialize the PDF comparison agent.
        
        Args:
            chat_client: Azure OpenAI chat client
            id: Executor ID
        """
        self.agent = chat_client.create_agent(
            instructions="""You are an expert document comparison specialist for pharmaceutical and regulatory documents.

Your task is to perform a thorough, word-by-word comparison of two PDF documents and identify ALL differences.

Instructions:
1. Compare the documents section by section, page by page
2. Identify three types of differences:
   - "added": Content present in document 2 but not in document 1
   - "removed": Content present in document 1 but not in document 2
   - "modified": Content that exists in both but has been changed

3. For each difference, provide:
   - Page number where the difference occurs
   - Section name
   - The original text (from document 1)
   - The new text (from document 2)
   - Brief context (surrounding text)

4. Be thorough - catch even small differences like:
   - Word changes
   - Number changes
   - Punctuation differences
   - Formatting differences that affect meaning

5. Output format: Return a JSON array of differences with this structure:
   [
     {
       "page_number": 1,
       "section": "Section name",
       "difference_type": "modified",
       "original_text": "original wording",
       "new_text": "new wording",
       "context": "surrounding text for reference"
     }
   ]

Be precise, thorough, and focus on substantive differences that matter for document comparison."""
        )
        super().__init__(id=id)
    
    @handler
    async def compare_pdfs(
        self,
        extractions: tuple[PDFExtraction, PDFExtraction],
        ctx: WorkflowContext[Never, ComparisonResult]
    ) -> None:
        """Compare two PDF extractions and find all differences.
        
        Args:
            extractions: Tuple containing two PDF extractions
            ctx: Workflow context for yielding final results
        """
        extraction1, extraction2 = extractions
        
        print(f"\n{'='*60}")
        print("STEP 2: Comparing Documents with AI")
        print(f"{'='*60}")
        print(f"Comparing: {extraction1.filename} vs {extraction2.filename}")
        
        # Prepare the comparison prompt with both documents
        comparison_prompt = self._build_comparison_prompt(extraction1, extraction2)
        
        # Create chat message and run the agent
        message = ChatMessage(Role.USER, text=comparison_prompt)
        response = await self.agent.run([message])
        
        # Parse the agent's response to extract differences
        differences = self._parse_comparison_response(response.text)
        
        # Create comparison result
        result = ComparisonResult(
            pdf1_name=extraction1.filename,
            pdf2_name=extraction2.filename,
            differences=differences,
            total_differences=len(differences)
        )
        
        print(f"\n✓ Found {len(differences)} differences")
        print(f"  - Added: {sum(1 for d in differences if d.difference_type == 'added')}")
        print(f"  - Removed: {sum(1 for d in differences if d.difference_type == 'removed')}")
        print(f"  - Modified: {sum(1 for d in differences if d.difference_type == 'modified')}")
        
        # Yield the final result
        await ctx.yield_output(result)
    
    def _build_comparison_prompt(
        self,
        extraction1: PDFExtraction,
        extraction2: PDFExtraction
    ) -> str:
        """Build a comprehensive prompt for the comparison agent.
        
        Args:
            extraction1: First PDF extraction
            extraction2: Second PDF extraction
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Compare these two documents and identify ALL differences:

DOCUMENT 1: {extraction1.filename}
Total pages: {extraction1.total_pages}
Content:
"""
        
        # Add sections from document 1
        for section in extraction1.sections[:50]:  # Limit to first 50 sections for token management
            prompt += f"\n[Page {section.page_number}, {section.section_title}]\n{section.content}\n"
        
        prompt += f"\n\nDOCUMENT 2: {extraction2.filename}\nTotal pages: {extraction2.total_pages}\nContent:\n"
        
        # Add sections from document 2
        for section in extraction2.sections[:50]:
            prompt += f"\n[Page {section.page_number}, {section.section_title}]\n{section.content}\n"
        
        prompt += """\n\nNow perform a detailed comparison and return a JSON array of all differences found.
Use the exact format specified in your instructions."""
        
        return prompt
    
    def _parse_comparison_response(self, response_text: str) -> list[TextDifference]:
        """Parse the agent's response and extract differences.
        
        Args:
            response_text: The agent's response text
            
        Returns:
            List of TextDifference objects
        """
        differences = []
        
        try:
            # Try to extract JSON from the response
            # The response might contain explanation text, so find the JSON array
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                diff_data = json.loads(json_str)
                
                # Convert to TextDifference objects
                for item in diff_data:
                    differences.append(TextDifference(
                        page_number=item.get("page_number", 0),
                        section=item.get("section", "Unknown"),
                        difference_type=item.get("difference_type", "modified"),
                        original_text=item.get("original_text", ""),
                        new_text=item.get("new_text", ""),
                        context=item.get("context", "")
                    ))
        except json.JSONDecodeError:
            print("⚠ Warning: Could not parse JSON from agent response")
            # Fallback: create a single difference with the full response
            differences.append(TextDifference(
                page_number=0,
                section="Analysis",
                difference_type="modified",
                original_text="See full analysis",
                new_text=response_text[:500],  # First 500 chars
                context="Agent provided non-JSON response"
            ))
        
        return differences
