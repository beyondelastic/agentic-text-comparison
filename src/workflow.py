"""Workflow orchestration for PDF comparison using Microsoft Agent Framework."""
import csv
import json
from pathlib import Path

from agent_framework import WorkflowBuilder
from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential

from .agents import PDFComparisonAgent, PDFExtractionAgent
from .config import AppConfig
from .models import ComparisonResult
from .pdf_extractor import PDFExtractor


class PDFComparisonWorkflow:
    """Orchestrates the multi-agent PDF comparison workflow."""
    
    def __init__(self, config: AppConfig):
        """Initialize the workflow with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        
        # Initialize Azure OpenAI chat client with temperature=0.0 for deterministic results
        self.chat_client = AzureOpenAIChatClient(
            endpoint=config.azure_openai.endpoint,
            credential=AzureKeyCredential(config.azure_openai.api_key),
            deployment_name=config.azure_openai.deployment_name,
            api_version=config.azure_openai.api_version,
            temperature=0.0
        )
        
        # Initialize PDF extractor
        self.pdf_extractor = PDFExtractor(config.azure_document_intelligence)
        
        # Create the agents
        self.extraction_agent = PDFExtractionAgent(
            pdf_extractor=self.pdf_extractor,
            chat_client=self.chat_client
        )
        
        self.comparison_agent = PDFComparisonAgent(
            chat_client=self.chat_client
        )
        
        # Build the workflow
        self.workflow = (
            WorkflowBuilder()
            .set_start_executor(self.extraction_agent)
            .add_edge(self.extraction_agent, self.comparison_agent)
            .build()
        )
    
    async def compare_pdfs(
        self,
        pdf1_path: Path,
        pdf2_path: Path
    ) -> ComparisonResult:
        """Execute the full comparison workflow.
        
        Args:
            pdf1_path: Path to first PDF file
            pdf2_path: Path to second PDF file
            
        Returns:
            ComparisonResult: The comparison results
        """
        print(f"\n{'='*60}")
        print("PDF COMPARISON WORKFLOW")
        print(f"{'='*60}")
        print(f"File 1: {pdf1_path.name}")
        print(f"File 2: {pdf2_path.name}")
        
        # Run the workflow with streaming to observe progress
        result = None
        events = await self.workflow.run((pdf1_path, pdf2_path))
        
        # Get the final output from the workflow
        outputs = events.get_outputs()
        if outputs:
            result = outputs[0]
        
        return result
    
    def save_results(self, result: ComparisonResult) -> None:
        """Save comparison results to files.
        
        Args:
            result: The comparison results to save
        """
        output_folder = self.config.output_folder
        
        # Save as JSON
        json_path = output_folder / "comparison_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved JSON results to {json_path}")
        
        # Save as CSV for easy viewing in spreadsheet applications
        csv_path = output_folder / "comparison_results.csv"
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "page_number",
                    "section",
                    "difference_type",
                    "original_text",
                    "new_text",
                    "context"
                ]
            )
            writer.writeheader()
            for diff in result.differences:
                writer.writerow(diff.to_dict())
        
        print(f"✓ Saved CSV results to {csv_path}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("COMPARISON SUMMARY")
        print(f"{'='*60}")
        print(f"Total differences found: {result.total_differences}")
        
        if result.differences:
            print(f"\nFirst 5 differences:")
            for i, diff in enumerate(result.differences[:5], 1):
                print(f"\n{i}. Page {diff.page_number} - {diff.section}")
                print(f"   Type: {diff.difference_type}")
                print(f"   Original: {diff.original_text[:100]}...")
                print(f"   New: {diff.new_text[:100]}...")
