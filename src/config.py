"""Configuration module for loading environment variables and Azure settings."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI configuration."""
    endpoint: str
    api_key: str
    deployment_name: str
    api_version: str


@dataclass
class AzureDocumentIntelligenceConfig:
    """Azure Document Intelligence configuration."""
    endpoint: str
    api_key: str


@dataclass
class AppConfig:
    """Application configuration."""
    azure_openai: AzureOpenAIConfig
    azure_document_intelligence: AzureDocumentIntelligenceConfig | None
    input_folder: Path
    output_folder: Path


def load_config() -> AppConfig:
    """Load application configuration from environment variables.
    
    Returns:
        AppConfig: Application configuration object
        
    Raises:
        ValueError: If required environment variables are missing
    """
    # Required Azure OpenAI settings
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    
    if not openai_endpoint or not openai_api_key:
        raise ValueError(
            "Missing required Azure OpenAI configuration. "
            "Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env file"
        )
    
    azure_openai = AzureOpenAIConfig(
        endpoint=openai_endpoint,
        api_key=openai_api_key,
        deployment_name=openai_deployment,
        api_version=openai_api_version
    )
    
    # Optional Azure Document Intelligence settings
    doc_intel_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    doc_intel_api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
    
    azure_doc_intelligence = None
    if doc_intel_endpoint and doc_intel_api_key:
        azure_doc_intelligence = AzureDocumentIntelligenceConfig(
            endpoint=doc_intel_endpoint,
            api_key=doc_intel_api_key
        )
    
    # Input/Output paths
    input_folder = Path(os.getenv("INPUT_FOLDER", "./input"))
    output_folder = Path(os.getenv("OUTPUT_FOLDER", "./output"))
    
    # Ensure output folder exists
    output_folder.mkdir(parents=True, exist_ok=True)
    
    return AppConfig(
        azure_openai=azure_openai,
        azure_document_intelligence=azure_doc_intelligence,
        input_folder=input_folder,
        output_folder=output_folder
    )
