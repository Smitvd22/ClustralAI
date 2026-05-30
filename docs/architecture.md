# Architecture

## System Overview

```mermaid
graph TB
    User([User / Client])

    subgraph "API Gateway Layer"
        RL[Rate Limiter<br/>slowapi]
        AUTH[API Key Auth<br/>X-API-Key Header]
    end

    subgraph "Security Layer"
        PG[Prompt Guard<br/>Regex + Scoring]
        EG[Exfiltration Guard<br/>Pattern Detection]
        IIG[Indirect Injection Guard<br/>Document Scanning]
        OF[Output Filter<br/>Secret + PII Scan]
        PII[PII Masker<br/>Logging Filter]
    end

    subgraph "RAG Pipeline"
        PDF[PDF Processor<br/>PyMuPDF]
        CHK[Text Chunker<br/>500/100 overlap]
        EMB[Embedding Service<br/>all-MiniLM-L6-v2]
        VS[Vector Store<br/>ChromaDB]
        RET[Retriever<br/>Top-K + Threshold]
        LLM[LLM Client<br/>Gemini 2.0 Flash]
    end

    subgraph "Render Infrastructure"
        ENV[Environment Variables<br/>Secrets]
        LOG[Render Logs<br/>Telemetry]
        DISK[Local Storage<br/>ChromaDB Ephemeral]
    end

    User -->|HTTPS| RL
    RL --> AUTH
    AUTH -->|POST /ingest| PDF
    AUTH -->|POST /query| PG

    PDF --> CHK --> EMB --> VS
    
    PG -->|Safe| EG
    EG -->|Safe| EMB
    EMB -->|Query Vector| RET
    RET --> IIG
    IIG -->|Safe Chunks| LLM
    LLM --> OF
    OF -->|Filtered| User

    PG -->|Blocked| User
    EG -->|Blocked| User

    ENV -.->|Auth| LLM
    VS -.->|Persist| DISK
    PII -.->|Filter| LOG
```

## Data Flow

### Ingestion Flow
```
PDF Upload → Validate (type, size) → Extract Text (PyMuPDF) 
→ Chunk (500 chars, 100 overlap) → Embed (all-MiniLM-L6-v2) 
→ Store (ChromaDB with metadata: filename, page, chunk_index)
```

### Query Flow
```
User Question → Rate Limit → API Auth → Prompt Guard → Exfiltration Guard
→ Embed Query → Retrieve Top-3 → Similarity Threshold Check
→ Indirect Injection Scan → Sanitize Context → LLM (Gemini)
→ Output Filter → Return Answer + Citations
```

## Component Details

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI | Async API with OpenAPI docs |
| Embeddings | all-MiniLM-L6-v2 | 384-dim local embeddings |
| Vector DB | ChromaDB | Persistent cosine similarity search |
| LLM | Gemini 2.0 Flash | Free-tier answer generation |
| PDF Parser | PyMuPDF | Text extraction with page tracking |
| Auth | Custom middleware | API key with constant-time comparison |
| Rate Limit | slowapi | In-memory per-IP throttling |
| Secrets | Render Environment Variables | Secure injection at runtime |
| Storage | Local Ephemeral Storage | Processed in-memory, ephemeral vectors |
| Monitoring | Render Logs | Standard stdout with PII masking |
| Container | Docker | Multi-stage, non-root, health checked |
| Deployment | Render Web Service | Free Tier compatible |
