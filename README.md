# SAR Narrative Generator

Enterprise-grade Suspicious Activity Report (SAR) assistant with deterministic controls, evidence boundaries, RAG retrieval, LLM generation, validation v2, explainability, review workflow, exports, and append-only audit logs.

## Project Status (as of February 2026)

**Current Phase:** Enterprise Feature Upgrade (backend + UI + exports)

### Completed Features
- Alert ingestion pipeline with JSON payload support and batch ingest
- Rule-based validation v1 and validation v2 with structured findings
- PII masking and evidence boundary enforcement
- Chroma vector database integration for document retrieval
- LLM-powered narrative generation (Ollama/Llama3.1) with mock LLM mode
- Explainability traces and contributing factors from risk engine
- Risk scoring with level/score/confidence and factor table
- Review workflow (submit/approve/reject/finalize) with versioning and audit trail
- Metrics endpoint for operational counters
- Export endpoints: PDF (two-part layout), JSON, audit log export
- FastAPI backend with RESTful endpoints; Streamlit UI with tabbed views (Upload, SAR, Evidence, Risk, Validation, Audit)
- Append-only SQLite audit logging and case persistence

### In Development
- Additional PDF template refinements against regulatory examples
- Expanded validation rules and tuning of hallucination guard
- Performance optimization for large batches

## System Architecture

### Backend Components
- **main.py** - FastAPI application, pipeline orchestration, endpoints (ingest/batch/review/exports/metrics)
- **llm.py** - LLM integration with Ollama or mock LLM
- **rag.py** - Document retrieval and vector database management
- **validation.py** - Rule-based validation engine (v1)
- **validation_v2.py** - Enhanced validation with structured results and hallucination guard
- **rules.py** - SAR compliance rule definitions
- **evidence.py** - Evidence extraction and boundary management
- **audit.py** - Audit logging system
- **db.py** - Database initialization and management
- **models.py** - Case schema including risk, validation v2, explainability, review history, versioning
- **config.py** - Configuration management
- **risk_engine.py** - Risk scoring, level/score/confidence, contributing factors
- **explainability.py** - Explainability trace generation and evidence mapping
- **review_workflow.py** - Submit/approve/reject/finalize logic with history
- **sar_formatter.py** - Narrative section ordering and formatting helpers
- **pdf_exporter.py** - Two-part SAR PDF layout (cover meta/risk/evidence + narrative table)
- **export/pdf_generator.py** - Shared PDF helpers
- **metrics.py** - Metrics aggregation for counters

### Data Structure
- **corpus/** - Sample documents for RAG
- **sample_alerts/** - Test alert payloads
- **chroma/** - Vector database storage
- **data/sar.db** - SQLite case and audit store (auto-created)

## Prerequisites
- Python 3.10+
- Ollama installed and running (optional - mock mode available)
- pip/Python package manager

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Pull Ollama Model (if using real LLM)
```bash
ollama pull llama3.1
```

### 3. Initialize Vector Database
```bash
python scripts/seed_data.py
```

## Running the Application

### Start Backend Server

**With Ollama LLM:**
```bash
uvicorn backend.main:app --reload
```

**With Mock LLM (for development):**
```bash
$env:USE_MOCK_LLM="true"
uvicorn backend.main:app --reload
```

### Launch Streamlit UI
```bash
streamlit run frontend/streamlit_app.py
```

## API Endpoints

### Core Operations
```bash
# Ingest an alert
curl -X POST http://localhost:8000/ingest-alert -H "Content-Type: application/json" -d @data/sample_alerts/alert_001.json

# List all cases
curl http://localhost:8000/cases

# Get specific case details
curl http://localhost:8000/cases/<case_id>

# View case audit trail
curl http://localhost:8000/cases/<case_id>/audit

# Export SAR PDF
curl http://localhost:8000/cases/<case_id>/export/pdf --output sar.pdf

# Export SAR JSON
curl http://localhost:8000/cases/<case_id>/export/json

# Metrics
curl http://localhost:8000/metrics
```

## Key Features

- **PII Protection** - Sensitive data is masked before reaching the LLM
- **Evidence Boundary** - Strict control over information scope
- **Append-Only Audit Trail** - Immutable record of all operations
- **Flexible LLM Backend** - Support for both real Ollama and mock implementations
- **Compliance Validation** - Rule-based verification of SAR requirements
- **Document Retrieval** - RAG integration with Chroma vector store

## Configuration Notes

- Backend runs on `http://localhost:8000`
- Ollama default endpoint: `http://localhost:11434`
- SQLite database location: `data/chroma/chroma.sqlite3`
- Mock mode enabled via `USE_MOCK_LLM` environment variable

## Troubleshooting

- **Ollama connection error**: Ensure Ollama is running (`ollama serve`)
- **Vector database issues**: Reinitialize with `python scripts/seed_data.py`
- **Port already in use**: Change port with `uvicorn backend.main:app --port 8001`
