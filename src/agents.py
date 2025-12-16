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
    
    This agent uses a hybrid two-phase approach:
    Phase 1: Deterministic diff algorithm finds ALL differences (free, fast)
    Phase 2: LLM adds semantic context and meaning to each difference (cost-effective)
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
        # Import diff tool here to avoid circular imports
        from .diff_tool import TextDiffer
        
        self.diff_tool = TextDiffer(similarity_threshold=0.6)
        
        self.agent = chat_client.create_agent(
            instructions="""You are an expert document analysis specialist for pharmaceutical and regulatory documents.

Your task is to provide semantic context and meaning for text differences that have already been identified.

You will receive a list of differences found by a diff algorithm. For each difference, provide:

1. **Context**: Explain where this change appears (what section, what topic)
2. **Semantic meaning**: What does this change mean? Why might it be important?
3. **Impact assessment**: Is this a minor change (typo, formatting) or major (content, meaning)?

Input format: You'll receive differences like:
- Type: added/removed/modified
- Page number
- Section title
- Original text
- New text

Output format: Return a JSON array with the SAME differences plus added context:
[
  {
    "page_number": 1,
    "section": "Introduction",
    "difference_type": "modified",
    "original_text": "version 1.0",
    "new_text": "version 2.0",
    "context": "Version number updated in the document header. This indicates a major revision."
  }
]

Be concise but informative. Focus on WHY the change matters, not just WHAT changed."""
        )
        super().__init__(id=id)
    
    @handler
    async def compare_pdfs(
        self,
        extractions: tuple[PDFExtraction, PDFExtraction],
        ctx: WorkflowContext[Never, ComparisonResult]
    ) -> None:
        """Compare two PDF extractions using a hybrid two-phase approach.
        
        Phase 1: Use diff algorithm to find ALL differences (deterministic, free)
        Phase 2: Use LLM to add semantic context (cost-effective, only for diffs)
        
        Args:
            extractions: Tuple containing two PDF extractions
            ctx: Workflow context for yielding final results
        """
        extraction1, extraction2 = extractions
        
        print(f"\n{'='*60}")
        print("STEP 2: Comparing Documents (Hybrid Approach)")
        print(f"{'='*60}")
        print(f"Comparing: {extraction1.filename} vs {extraction2.filename}")
        
        # PHASE 1: Deterministic diff (no AI cost)
        print("\nPhase 1: Running deterministic diff algorithm...")
        raw_differences = self.diff_tool.compare_extractions(extraction1, extraction2)
        print(f"✓ Found {len(raw_differences)} differences using diff algorithm")
        print(f"  - Added: {sum(1 for d in raw_differences if d.difference_type == 'added')}")
        print(f"  - Removed: {sum(1 for d in raw_differences if d.difference_type == 'removed')}")
        print(f"  - Modified: {sum(1 for d in raw_differences if d.difference_type == 'modified')}")
        
        if not raw_differences:
            print("\n✓ No differences found - documents are identical!")
            result = ComparisonResult(
                pdf1_name=extraction1.filename,
                pdf2_name=extraction2.filename,
                differences=[],
                total_differences=0
            )
            await ctx.yield_output(result)
            return
        
        # PHASE 2: LLM enhancement (only for differences found)
        print(f"\nPhase 2: Adding semantic context with AI (processing {len(raw_differences)} differences)...")
        enhanced_differences = await self._enhance_differences_with_llm(raw_differences)
        
        # Create comparison result
        result = ComparisonResult(
            pdf1_name=extraction1.filename,
            pdf2_name=extraction2.filename,
            differences=enhanced_differences,
            total_differences=len(enhanced_differences)
        )
        
        print(f"\n✓ Comparison complete with AI-enhanced context")
        
        # Yield the final result
        await ctx.yield_output(result)
    
    async def _enhance_differences_with_llm(
        self,
        raw_differences: list
    ) -> list[TextDifference]:
        """Enhance raw differences with semantic context using LLM.
        
        This sends only the differences (not full documents) to the LLM
        for context enhancement, dramatically reducing token usage.
        
        Args:
            raw_differences: List of RawDifference objects from diff algorithm
            
        Returns:
            List of TextDifference objects with AI-generated context
        """
        # Group differences for efficient batch processing
        grouped_diffs = self.diff_tool.group_related_differences(raw_differences, max_distance=5)
        
        enhanced_differences = []
        total_groups = len(grouped_diffs)
        
        for idx, diff_group in enumerate(grouped_diffs, 1):
            print(f"  Processing group {idx}/{total_groups} ({len(diff_group)} differences)...")
            
            # Build prompt with just these differences
            prompt = self._build_enhancement_prompt(diff_group)
            
            # Send to LLM
            message = ChatMessage(Role.USER, text=prompt)
            response = await self.agent.run([message])
            
            # Parse response
            enhanced = self._parse_enhancement_response(response.text, diff_group)
            enhanced_differences.extend(enhanced)
        
        return enhanced_differences
    
    def _build_enhancement_prompt(self, diff_group: list) -> str:
        """Build a prompt for LLM to enhance a group of differences.
        
        Args:
            diff_group: List of RawDifference objects
            
        Returns:
            Formatted prompt string
        """
        prompt = """Please provide semantic context for these differences found in the document:

"""
        
        for i, diff in enumerate(diff_group, 1):
            prompt += f"""{i}. [{diff.difference_type.upper()}] Page {diff.page_number}, {diff.section_title}
   Original: "{diff.original_text}"
   New: "{diff.new_text}"

"""
        
        prompt += """For each difference, provide context explaining:
- Where this appears in the document
- What this change means
- Why it might be important

Return as JSON array matching the format in your instructions."""
        
        return prompt
    
    def _parse_enhancement_response(
        self,
        response_text: str,
        diff_group: list
    ) -> list[TextDifference]:
        """Parse LLM response and combine with raw differences.
        
        Args:
            response_text: LLM response text
            diff_group: Original RawDifference objects
            
        Returns:
            List of TextDifference objects with context
        """
        differences = []
        
        try:
            # Try to extract JSON from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                enhanced_data = json.loads(json_str)
                
                # Match enhanced data with raw differences
                for i, item in enumerate(enhanced_data):
                    # Get corresponding raw diff (fallback if mismatch)
                    raw_diff = diff_group[i] if i < len(diff_group) else diff_group[0]
                    
                    differences.append(TextDifference(
                        page_number=item.get("page_number", raw_diff.page_number),
                        section=item.get("section", raw_diff.section_title),
                        difference_type=item.get("difference_type", raw_diff.difference_type),
                        original_text=item.get("original_text", raw_diff.original_text),
                        new_text=item.get("new_text", raw_diff.new_text),
                        context=item.get("context", "No context provided")
                    ))
            else:
                # Fallback: use raw differences with generic context
                for raw_diff in diff_group:
                    differences.append(TextDifference(
                        page_number=raw_diff.page_number,
                        section=raw_diff.section_title,
                        difference_type=raw_diff.difference_type,
                        original_text=raw_diff.original_text,
                        new_text=raw_diff.new_text,
                        context=f"Found on page {raw_diff.page_number} in {raw_diff.section_title}"
                    ))
        
        except json.JSONDecodeError:
            print("  ⚠ Warning: Could not parse LLM response, using raw differences")
            # Fallback to raw differences with basic context
            for raw_diff in diff_group:
                differences.append(TextDifference(
                    page_number=raw_diff.page_number,
                    section=raw_diff.section_title,
                    difference_type=raw_diff.difference_type,
                    original_text=raw_diff.original_text,
                    new_text=raw_diff.new_text,
                    context=f"Found on page {raw_diff.page_number}"
                ))
        
        return differences
