# Configuration Generator Project

AI-powered network configuration generator for Alteon/Radware load balancers using RAG (Retrieval Augmented Generation).

## Quick Start

### Prerequisites
```bash
# 1. Activate virtual environment
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup OpenAI API key (for Phase 2)
python setup_env.py
# Then edit .env and add your key
```

See [Environment Setup Guide](docs/ENV_SETUP.md) for detailed instructions.

## Project Status: Phase 1 Complete ✓

### Phase 1: Ingest & Parse  
**Status:** ✅ Complete

Parses raw configuration files into structured module blocks with:
- Hierarchical module detection
- Multi-line content handling (certificates, scripts)
- Duplicate detection across multiple configs
- JSON storage for downstream processing

**Usage:**
```bash
# Add configuration files to configs/ directory
# Then run ingestion:
python ingest_configs.py
```

## Project Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Ingest & Parse (✅ COMPLETE)                        │
│ Raw Configs → Parser → Module Blocks → JSON Storage        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Normalize & Template (🔜 NEXT)                     │
│ Module Blocks → AI Analysis → Templated Modules            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Embed & Store                                      │
│ Templated Modules + Metadata → Embeddings → ChromaDB       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Retrieve (RAG)                                     │
│ Customer Natural Language → Query Embedding → Modules      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: Assemble Final Config                             │
│ Retrieved Modules + Values → Python Assembly → Config      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 6: Validate & Render                                  │
│ Draft Config → Validation → Final Config File              │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
gencfg/
├── configs/                 # Raw configuration files (.txt, .cfg)
│   ├── sample_config_1.txt
│   └── sample_config_2.txt
├── data/
│   └── parsed/             # Parsed module JSON files (gitignored)
├── utils/
│   ├── __init__.py
│   └── parser.py           # Phase 1: Configuration parser
├── ingest_configs.py       # Main ingestion script
├── test_parser.py          # Quick parser test
└── README.md
```

## Project Overview

This system parses existing network configurations, extracts reusable module templates, stores them in a vector database, and generates new configurations based on natural language customer requirements.

**Target Platform:** Alteon/Radware Load Balancers

## Architecture Phases

1. **Ingest & Parse** - Parse raw configurations into module blocks
2. **Normalize & Template** - Convert to templates with placeholders
3. **Embed & Store** - Store in vector database (ChromaDB)
4. **Retrieve (RAG)** - Find relevant modules based on customer intent
5. **Assemble** - Generate configuration from templates
6. **Validate & Render** - Final validation and output

## Current Status

✅ **Phase 1 Complete:** Configuration Parser

### Phase 1: Configuration Parser

Located in `utils/parser.py`

**Features:**
- Parses hierarchical CLI-style configurations
- Extracts module blocks with paths and indices
- Handles multi-line content (certificates, scripts)
- Detects action commands
- Normalizes whitespace
- Extracts metadata from multi-line modules

**Module Types Supported:**
- Standard modules (key-value pairs)
- Indexed modules (numeric and named)
- Action commands (e.g., `/c/slb/pip/add 10.250.20.29 820`)
- Empty modules (declarations only)
- Certificate imports (preserves PEM format)
- Script imports (preserves code exactly)

## Quick Start

### Setup

```bash
# Create virtual environment (already done)
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies (when available)
pip install -r requirements.txt
```

### Test Phase 1 Parser

```bash
python test_parser.py
```

## Usage Example

```python
from utils.parser import ConfigParser, ModuleType

# Parse a configuration file
parser = ConfigParser()
with open('config.txt', 'r') as f:
    modules = parser.parse(f.read())

# Get statistics
stats = parser.get_module_stats()
print(f"Parsed {stats['total_modules']} modules")

# Filter by type
cert_modules = parser.get_modules_by_type(ModuleType.MULTILINE_CERT)
for module in cert_modules:
    print(f"Certificate: {module.multiline_metadata['cert_name']}")

# Filter by path
interfaces = parser.get_modules_by_path('/c/l3/if')
for iface in interfaces:
    print(f"Interface {iface.index}")
```

## Project Structure

```
gencfg/
├── utils/
│   ├── __init__.py
│   └── parser.py          # Phase 1: Configuration parser
├── data/                   # Sample configurations
├── test_parser.py         # Phase 1 test script
├── .gitignore
└── README.md
```

## Next Steps

- [ ] Phase 2: AI-assisted normalization and templating
- [ ] Phase 3: Vector database setup (ChromaDB)
- [ ] Phase 4: RAG retrieval system
- [ ] Phase 5: Configuration assembly engine
- [ ] Phase 6: Validation framework

## Development Notes

**Design Principles:**
- Deterministic output is critical
- AI suggests, Python generates
- Templates are source of truth
- Multi-line content preserved exactly
- Module order matters

**Parser Specifications:**
- Whitespace normalized
- No syntax validation (for now)
- Action commands treated specially
- Metadata extracted from multi-line modules

---

## Phase 2 Design (Approved)

Phase 2 design is complete and approved. See [docs/PHASE2_DESIGN.md](docs/PHASE2_DESIGN.md) for full details.

**Key Decisions:**
- **AI Provider:** OpenAI GPT-4
- **Placeholder Style:** Descriptive names (e.g., `{{management_ip_address}}`)
- **Template Strategy:** One template with all optional parameters
- **Default Threshold:** 70% occurrence
- **Cost Estimate:** ~$2.50 per full run

**Quick Reference:** [docs/PHASE2_QUICK_REF.md](docs/PHASE2_QUICK_REF.md)

---

## License

TBD

## Contributors

TBD
