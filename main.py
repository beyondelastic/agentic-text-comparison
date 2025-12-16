"""Main entry point for the PDF comparison application."""
import asyncio
import sys
from pathlib import Path

from colorama import Fore, Style, init

from src.config import load_config
from src.workflow import PDFComparisonWorkflow

# Initialize colorama for colored terminal output
init(autoreset=True)


def find_pdf_files(input_folder: Path) -> list[Path]:
    """Find all PDF files in the input folder.
    
    Args:
        input_folder: Path to the input folder
        
    Returns:
        List of PDF file paths
    """
    pdf_files = list(input_folder.glob("*.pdf"))
    return sorted(pdf_files)


def print_banner():
    """Print application banner."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}  AI Agent-Based PDF Comparison System")
    print(f"{Fore.CYAN}  Powered by Microsoft Agent Framework & Azure OpenAI")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


async def main():
    """Main application entry point."""
    try:
        print_banner()
        
        # Load configuration
        print(f"{Fore.YELLOW}Loading configuration...{Style.RESET_ALL}")
        config = load_config()
        print(f"{Fore.GREEN}✓ Configuration loaded successfully{Style.RESET_ALL}")
        
        # Find PDF files in input folder
        print(f"\n{Fore.YELLOW}Scanning input folder: {config.input_folder}{Style.RESET_ALL}")
        pdf_files = find_pdf_files(config.input_folder)
        
        if len(pdf_files) < 2:
            print(f"{Fore.RED}✗ Error: Need at least 2 PDF files in the input folder{Style.RESET_ALL}")
            print(f"{Fore.RED}  Found {len(pdf_files)} PDF file(s){Style.RESET_ALL}")
            sys.exit(1)
        
        if len(pdf_files) > 2:
            print(f"{Fore.YELLOW}⚠ Found {len(pdf_files)} PDF files. Using the first two:{Style.RESET_ALL}")
        
        pdf1_path = pdf_files[0]
        pdf2_path = pdf_files[1]
        
        print(f"{Fore.GREEN}✓ Found PDF files:{Style.RESET_ALL}")
        print(f"  1. {pdf1_path.name}")
        print(f"  2. {pdf2_path.name}")
        
        # Initialize the workflow
        print(f"\n{Fore.YELLOW}Initializing AI agents and workflow...{Style.RESET_ALL}")
        workflow = PDFComparisonWorkflow(config)
        print(f"{Fore.GREEN}✓ Workflow initialized{Style.RESET_ALL}")
        
        # Execute the comparison
        print(f"\n{Fore.CYAN}Starting comparison workflow...{Style.RESET_ALL}")
        result = await workflow.compare_pdfs(pdf1_path, pdf2_path)
        
        if result:
            # Save results
            workflow.save_results(result)
            
            print(f"\n{Fore.GREEN}{'='*60}")
            print(f"{Fore.GREEN}✓ Comparison completed successfully!")
            print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
            print(f"\nResults saved to: {config.output_folder}")
            print(f"  - comparison_results.json (detailed JSON)")
            print(f"  - comparison_results.csv (spreadsheet format)")
        else:
            print(f"\n{Fore.RED}✗ No results returned from workflow{Style.RESET_ALL}")
            sys.exit(1)
    
    except FileNotFoundError as e:
        print(f"\n{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    except ValueError as e:
        print(f"\n{Fore.RED}✗ Configuration Error: {e}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Please check your .env file and ensure all required variables are set.{Style.RESET_ALL}")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n{Fore.RED}✗ Unexpected error: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
