# Configuration Generator Project

AI-powered network configuration generator for load balancers using RAG (Retrieval Augmented Generation).

## Quick Start

### Prerequisites
```bash
# 1. Activate virtual environment
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup OpenAI API key
python setup_env.py
# Then edit .env and add your key
```

See [Environment Setup Guide](docs/ENV_SETUP.md) for detailed instructions.

### Generate Configuration (Phase 5 Complete!)
```bash
# Interactive mode
python generate_config.py --mode interactive

# Single requirement
python generate_config.py --mode single -r "Create VIP 10.1.1.100 on port 443 with SSL offload" --verbose

# Batch mode
python generate_config.py --mode batch -f requirements.txt -o output/
```

## Project Status: Phase 5 Complete ✓

### ✅ Phase 1: Ingest & Parse (COMPLETE)
**Status:** ✅ Complete

Parses raw configuration files into structured module blocks with:
- Hierarchical module detection
- Multi-line content handling (certificates, scripts)
- Duplicate detection across multiple configs
- JSON storage for downstream processing

**Usage:**
```bash
python ingest_configs.py
```

### ✅ Phase 2: Normalize & Template (COMPLETE)
**Status:** ✅ Complete

AI-powered conversion of module blocks into reusable templates:
- GPT-4 analyzes patterns across multiple config instances
- Generates descriptive placeholder names
- Learns parameter types, defaults, and validations
- Extracts categories, tags, and descriptions
- Computes confidence scores for defaults

**Usage:**
```bash
python normalize_configs.py
```

**Output:** `data/templates/templated_modules_*.json`

### ✅ Phase 3: Embed & Store (COMPLETE)
**Status:** ✅ Complete

Vector database storage with ChromaDB:
- Generates embeddings for template searchability
- Stores templates with rich metadata
- Enables semantic similarity search
- Persistent storage in `data/vectordb/`

**Usage:**
```bash
python embed_templates.py
```

### ✅ Phase 4: Retrieve (RAG) (COMPLETE)
**Status:** ✅ Complete

Intelligent template retrieval system:
- Parses natural language requirements
- Multi-factor relevance ranking (semantic + category + params)
- Query generation with filters
- Returns ranked templates with explanations

**Components:**
- `phase4/requirements_parser.py` - NLP parsing
- `phase4/query_generator.py` - Vector queries
- `phase4/template_retriever.py` - ChromaDB search
- `phase4/relevance_ranker.py` - Multi-factor scoring

### ✅ Phase 5: Assembly & Generation (COMPLETE)
**Status:** ✅ Complete

End-to-end configuration generation pipeline:
- Value extraction from requirements (IPs, ports, VLANs)
- Intelligent parameter matching with confidence scores
- Template assembly with placeholder replacement
- Dependency resolution and module ordering
- Final configuration formatting

**Components:**
- `phase5/value_extractor.py` - Extract concrete values
- `phase5/parameter_matcher.py` - Match values to parameters
- `phase5/template_assembler.py` - Fill templates
- `phase5/dependency_resolver.py` - Order modules
- `phase5/config_generator.py` - Format output
- `generate_config.py` - Main orchestrator

**Usage:**
```bash
# Interactive mode
python generate_config.py --mode interactive

# Single requirement
python generate_config.py --mode single -r "Create VIP 10.1.1.100 on port 443" --verbose

# Batch processing
python generate_config.py --mode batch -f requirements.txt -o output/
```

### 🔜 Phase 6: Validate & Render (NEXT)
**Status:** 🔜 Planned

Final validation and output rendering:
- Syntax validation
- Type checking
- Cross-reference validation
- Dependency verification
- Output formatting options

## Project Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Ingest & Parse (✅ COMPLETE)                        │
│ Raw Configs → Parser → Module Blocks → JSON Storage        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Normalize & Template (✅ COMPLETE)                  │
│ Module Blocks → GPT-4 Analysis → Templated Modules         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Embed & Store (✅ COMPLETE)                         │
│ Templated Modules + Metadata → Embeddings → ChromaDB       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 4: Retrieve (RAG) (✅ COMPLETE)                        │
│ Natural Language → Parse → Query → Ranked Templates        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: Assembly & Generation (✅ COMPLETE)                 │
│ Requirements → Extract Values → Match → Assemble → Config  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 6: Validate & Render (🔜 NEXT)                        │
│ Draft Config → Validation → Final Config File              │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
gencfg/
├── configs/                    # Raw configuration files (.txt, .cfg)
├── data/
│   ├── parsed/                # Phase 1: Parsed module JSON files
│   ├── templates/             # Phase 2: Templated modules with metadata
│   ├── vectordb/              # Phase 3: ChromaDB persistent storage
│   └── results/               # Processing results and logs
├── output/                     # Generated configurations
├── docs/                       # Documentation
│   ├── ENV_SETUP.md
│   ├── PHASE2_DESIGN.md
│   └── PHASE2_QUICK_REF.md
├── utils/
│   ├── __init__.py
│   └── parser.py              # Phase 1: Configuration parser
├── phase2/                     # AI-powered templating
│   ├── __init__.py
│   ├── ai_processor.py        # GPT-4 integration
│   ├── template_generator.py  # Template creation
│   ├── default_learner.py     # Learn parameter defaults
│   └── metadata_extractor.py  # Extract categories/tags
├── phase3/                     # Vector database
│   ├── __init__.py
│   ├── embedding_generator.py # Generate embeddings
│   ├── vector_store.py        # ChromaDB wrapper
│   └── document_builder.py    # Build searchable documents
├── phase4/                     # RAG retrieval
│   ├── __init__.py
│   ├── requirements_parser.py # Parse natural language
│   ├── query_generator.py     # Generate vector queries
│   ├── template_retriever.py  # ChromaDB search
│   └── relevance_ranker.py    # Multi-factor ranking
├── phase5/                     # Assembly & generation
│   ├── __init__.py
│   ├── value_extractor.py     # Extract values from requirements
│   ├── parameter_matcher.py   # Match values to parameters
│   ├── template_assembler.py  # Fill templates
│   ├── dependency_resolver.py # Order modules by dependencies
│   └── config_generator.py    # Format final output
├── ingest_configs.py          # Phase 1: Main ingestion script
├── normalize_configs.py       # Phase 2: Main templating script
├── embed_templates.py         # Phase 3: Main embedding script
├── generate_config.py         # Phase 5: Main generation script (interactive/batch/single)
├── test_parser.py             # Phase 1: Quick parser test
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (API keys)
├── .gitignore
└── README.md
```

## Current Features

### End-to-End Configuration Generation
- **Natural Language Input**: "Create VIP 10.1.1.100 on port 443 with SSL offload"
- **Automatic Value Extraction**: IPs, ports, VLANs, names from requirements
- **Intelligent Template Retrieval**: Semantic search + multi-factor ranking
- **Smart Parameter Matching**: Type compatibility + context + keywords
- **Dependency Ordering**: Topological sort ensures correct module sequence
- **Multiple Modes**: Interactive, single requirement, or batch processing

### Example Output
Input: `"Create VIP 10.1.1.100 on port 443 with SSL offload"`

Output:
```
/c/slb/real 1
    ipver v4
    rip 10.1.1.100

/c/slb/group 1
    ipver v4
    add 1

/c/slb/virt 1
    ipver v4
    vip 10.1.1.100

/c/slb/ssl/certs/import cert

apply
save
```

## Known Limitations & Upcoming Enhancements

### Phase 4 Enhancements (Planned)
- Better template relevance filtering
- Context-aware template selection
- Category-based filtering

### Phase 5 Enhancements (Planned)
- Inter-module relationship tracking (group.add → real.index)
- Sub-module support (`/c/slb/virt 1/service 443 https`)
- Improved default value usage
- Better index assignment strategies

### Phase 6 (Next)
- Configuration validation
- Type checking
- Cross-reference verification
- Syntax validation

## Development Notes

**Design Principles:**
- AI suggests, Python generates (deterministic)
- Templates are source of truth
- Multi-line content preserved exactly
- Module order matters for dependencies
- No hallucination - only template-based generation

**Technology Stack:**
- **Language**: Python 3.13.9
- **AI**: OpenAI GPT-4 Turbo (templating only)
- **Vector DB**: ChromaDB (persistent storage)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Architecture**: RAG (Retrieval Augmented Generation)

**Performance:**
- Phase 2 (Templating): ~$2.50 per run, ~2 minutes
- Phase 3 (Embedding): < 1 second
- Phase 4 (Retrieval): < 1 second
- Phase 5 (Generation): < 1 second
- **Total**: Generate configs in under 2 seconds after initial setup

---

## Documentation

- [Environment Setup Guide](docs/ENV_SETUP.md) - Python, venv, API keys
- [Phase 2 Design](docs/PHASE2_DESIGN.md) - Templating architecture
- [Phase 2 Quick Reference](docs/PHASE2_QUICK_REF.md) - Command reference

---

## Recent Changes (Dec 23, 2025)

### Phase 5 Complete
- Implemented complete assembly and generation pipeline
- Created 6 new components (1,722 lines of code)
- End-to-end testing successful
- Interactive/batch/single modes working
- Configuration export with timestamps and metadata

### Known Issues
- Template retrieval may include irrelevant modules
- Missing inter-module relationship tracking
- No sub-module support yet (e.g., virt/service)
- Some required parameters use generic defaults

### Next Session Goals
1. Enhance Phase 4 template filtering
2. Add inter-module relationship intelligence
3. Implement sub-module support
4. Begin Phase 6 validation system

---

## License

TBD

## Contributors

TBD
