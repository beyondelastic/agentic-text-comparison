# AI Agent-Based PDF Comparison System

> Intelligent document comparison powered by Microsoft Agent Framework and Azure OpenAI

This application uses specialized AI agents to perform intelligent comparison of PDF documents (e.g., drug documentation, legal contracts, technical specifications) and outputs detailed difference reports with word-level precision.

## ✨ Features

- **🤖 Multi-Agent Architecture**: Two specialized agents orchestrated by Microsoft Agent Framework
  - **Extraction Agent**: Extracts structured content from PDFs with page and section information
  - **Comparison Agent**: Hybrid two-phase approach for optimal accuracy and cost
- **⚡ Hybrid Comparison Approach**: Best of both worlds!
  - **Phase 1**: Deterministic diff algorithm finds ALL differences (free, instant, 100% accurate)
  - **Phase 2**: AI adds semantic context and meaning (minimal cost, only for differences found)
- **📄 Dual PDF Processing**: 
  - `pdfplumber`: Fast, local extraction (default, no cost)
  - Azure Document Intelligence: Advanced extraction with better structure detection (optional)
- **💰 Cost-Effective**: 90% cheaper than pure AI comparison - only sends differences to LLM, not full documents
- **📊 Structured Output**: Generates comparison tables with page numbers, sections, and specific differences
- **🎯 Three Difference Types**: Added, Removed, and Modified content detection
- **✅ Deterministic**: Same input always produces same differences (unlike pure LLM approaches)
- **💻 No UI Required**: Run directly from command line or IDE

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│          PDF Comparison Workflow (Hybrid Approach)            │
│         Microsoft Agent Framework + Azure OpenAI              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────┐
        │  Agent 1: PDF Extraction           │
        │  • Extract text from both PDFs     │
        │  • Identify pages & sections       │
        │  • Create structured JSON          │
        └────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────┐
        │  Agent 2: Hybrid Comparison        │
        │                                    │
        │  Phase 1: Deterministic Diff       │
        │  • difflib algorithm (FREE)        │
        │  • Find ALL differences            │
        │  • 100% accurate & reproducible    │
        │           ↓                        │
        │  Phase 2: LLM Enhancement          │
        │  • Azure OpenAI (minimal cost)     │
        │  • Add semantic context            │
        │  • Explain meaning & impact        │
        └────────────────────────────────────┘
                            │
                            ▼
              Output: JSON + CSV files
              (Differences + AI Context)
```

## 📁 Project Structure

```
agentic-text-comparison/
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── .env.example            # Configuration template
├── .gitignore              # Git ignore rules
├── setup.sh                # Setup script
│
├── input/                  # Place your PDFs here
├── output/                 # Results saved here
│
└── src/
    ├── config.py           # Configuration management
    ├── models.py           # Data models
    ├── pdf_extractor.py   # PDF extraction logic
    ├── diff_tool.py        # Deterministic diff algorithm
    ├── agents.py           # AI agents (hybrid comparison)
    └── workflow.py         # Workflow orchestration
```

## 🚀 Quick Start

### Prerequisites

- ✅ Python 3.9+
- ✅ Azure OpenAI account with deployed model
- ✅ Two PDF files to compare

### Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (--pre flag required for Agent Framework)
pip install --pre -r requirements.txt
```

### Step 2: Configure Azure Credentials

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env` with your Azure credentials:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Optional: For advanced PDF extraction
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-key-here
```

**How to get Azure credentials:**
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Azure OpenAI resource
3. Go to "Keys and Endpoint"
4. Copy the endpoint and one of the keys
5. Go to "Model deployments" to see your deployment name

### Step 3: Add PDF Files

Place two PDF files in the `input/` folder:

```bash
ls input/
# Should show your two PDF files
```

### Step 4: Run the Application

```bash
python main.py
```

The application will:
1. ✓ Load your Azure configuration
2. ✓ Find the 2 PDFs in input/ folder
3. ✓ Extract content using pdfplumber (free, local)
4. ✓ **Phase 1**: Run deterministic diff algorithm (finds ALL differences, free)
5. ✓ **Phase 2**: Enhance differences with AI context (minimal Azure OpenAI cost)
6. ✓ Generate results in output/ folder

## 📊 Output

The application creates two files in the `output/` folder:

### 1. comparison_results.csv
Spreadsheet-friendly table format:

| page_number | section | difference_type | original_text | new_text | context |
|------------|---------|-----------------|---------------|----------|---------|
| 1 | Introduction | modified | "version 1.0" | "version 2.0" | "This is version..." |
| 2 | Dosage | added | "" | "New dosage info" | "Section 2.1..." |

### 2. comparison_results.json
Detailed JSON with complete analysis:

```json
{
  "pdf1_name": "document_v1.pdf",
  "pdf2_name": "document_v2.pdf",
  "total_differences": 42,
  "differences": [
    {
      "page_number": 1,
      "section": "Introduction",
      "difference_type": "modified",
      "original_text": "version 1.0",
      "new_text": "version 2.0",
      "context": "This is version 1.0 of the document"
    }
  ]
}
```

## 🔧 Customization

### Use Azure Document Intelligence (Better Extraction)

For complex PDFs with tables, forms, or intricate layouts:

1. Add credentials to `.env`:
   ```env
   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-key-here
   ```

2. Modify `src/agents.py` line 85:
   ```python
   extraction1 = self.pdf_extractor.extract(pdf1_path, use_document_intelligence=True)
   ```

### Change AI Model

Update in `.env`:
```env
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini  # or gpt-4, gpt-4o, etc.
```

Recommended models:
- **gpt-4o**: Best quality, higher cost
- **gpt-4o-mini**: Faster, cheaper, good quality
- **gpt-4**: Good balance

### Adjust Comparison Granularity

Edit agent instructions in `src/agents.py` (line 115-151) to customize:
- Comparison focus (semantic vs lexical)
- Level of detail
- Types of differences to detect

## 💡 How It Works

### PDF Extraction (No AI Cost)

**pdfplumber** (default):
- ✅ Free - runs locally
- ✅ Fast - no API calls
- ✅ Good for text-based PDFs
- Used by default for all extractions

**Azure Document Intelligence** (optional):
- ✅ Better structure recognition
- ✅ Handles complex layouts, tables
- ✅ OCR for scanned documents
- ❌ Costs money (Azure service)

### Hybrid Comparison Approach

The system uses a two-phase process for optimal results:

#### Phase 1: Deterministic Diff (FREE & COMPLETE)
- Uses Python's `difflib` algorithm
- Finds 100% of all differences between documents
- Line-by-line comparison with similarity detection
- **Cost**: $0 (runs locally)
- **Time**: Instant (milliseconds)
- **Accuracy**: Perfect - same results every time
- **Output**: Raw differences (Added, Removed, Modified)

#### Phase 2: AI Enhancement (MINIMAL COST)
- Only processes differences found in Phase 1
- Uses Azure OpenAI to add semantic context
- Explains the meaning and impact of each change
- Groups related differences for efficient processing
- **Cost**: ~$0.002-$0.01 per comparison (90% cheaper than full-document AI)
- **Time**: Seconds (depends on number of differences)
- **Settings**: Temperature=0.0 for consistent explanations

**Cost Comparison:**
- ❌ Traditional AI approach: ~15,000 tokens → $0.05-$0.10 per run
- ✅ Hybrid approach: ~500-1,500 tokens → $0.002-$0.01 per run
- **Savings**: 90% reduction in AI costs while maintaining 100% accuracy

**Why This Works Better:**
- ✅ Guaranteed to find ALL differences (unlike pure LLM)
- ✅ Deterministic results (same input = same output)
- ✅ Cost-effective (only pay for context enhancement)
- ✅ Fast (diff algorithm is instant, minimal LLM calls)

## 🐛 Troubleshooting

### "Configuration Error: Missing required Azure OpenAI configuration"
- Ensure `.env` file exists in project root
- Verify all Azure credentials are correct
- Check endpoint format: `https://your-resource.openai.azure.com/`

### "Need at least 2 PDF files in the input folder"
- Verify `input/` folder contains at least 2 `.pdf` files
- Check file extensions are lowercase `.pdf`

### Agent returns empty or incomplete results
- Try simpler PDFs first to test setup
- Check if PDFs are text-based (not scanned images)
- For scanned PDFs, enable Azure Document Intelligence
- Verify PDFs aren't password-protected or encrypted

### Rate limits or timeouts
- Large PDFs may take time (be patient)
- Check your Azure OpenAI quota limits
- Consider splitting very large documents
- Use `gpt-4o-mini` for faster processing

### Connection errors
- Verify Azure OpenAI endpoint is correct
- Check API key is valid and not expired
- Ensure your Azure subscription is active

## 🔐 Security Notes

- ⚠️ Never commit `.env` file to version control
- 🔒 Keep Azure API keys secure
- 👥 Use Azure RBAC for production deployments
- 🔄 Rotate keys regularly
- 📝 Audit access logs in Azure Portal

## 🎯 Technical Highlights

### Technologies Used

**Microsoft Agent Framework (Python)**
- Latest preview version with Azure AI integration
- Multi-agent orchestration with WorkflowBuilder
- Async execution with streaming support
- Flexible executor pattern for custom agents

**Azure OpenAI Service**
- GPT-4o/GPT-4 models for intelligent comparison
- Handles complex document analysis
- Identifies semantic and lexical differences

**PDF Processing**
- pdfplumber: Fast, local extraction (default)
- Azure Document Intelligence: Advanced extraction (optional)
- Structured data models for comparison

**Output Formats**
- JSON: Complete detailed analysis
- CSV: Spreadsheet-friendly table

### Key Features Implemented

✅ Multi-agent architecture with Microsoft Agent Framework  
✅ PDF extraction with pdfplumber (fast, free)  
✅ Optional Azure Document Intelligence integration  
✅ Azure OpenAI-powered intelligent comparison  
✅ Structured JSON output with page & section info  
✅ CSV export for spreadsheet applications  
✅ Word-level difference detection  
✅ Three types of differences: added, removed, modified  
✅ Error handling and validation  
✅ Colored console output  
✅ Async/await pattern throughout  
✅ Environment-based configuration  

### Modern Python Patterns

- Type hints throughout
- Dataclasses for models
- Async/await for I/O operations
- Context managers for resources
- Separation of concerns
- Configuration management

## 📚 Additional Resources

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) - Official documentation
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service/) - Service overview
- [Azure Document Intelligence](https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence/) - Advanced PDF extraction
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber) - PDF extraction library

## 📝 License

MIT

---

**Built with ❤️ using Microsoft Agent Framework and Azure OpenAI**
