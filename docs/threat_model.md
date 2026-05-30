# Threat Model

## Threat Analysis

| # | Threat | Risk Level | Attack Vector | Mitigation | Status |
|---|--------|-----------|---------------|------------|--------|
| 1 | **Direct Prompt Injection** | HIGH | User crafts query to override system prompt (e.g., "ignore previous instructions") | Regex pattern matching with weighted scoring (12+ patterns), cumulative threshold blocking, hardened system prompt | ✅ Implemented |
| 2 | **Indirect Prompt Injection** | HIGH | Malicious instructions embedded in uploaded PDF documents | Document content scanned for injection patterns before LLM processing, content wrapped in security delimiters, system prompt explicitly instructs to never follow document instructions | ✅ Implemented |
| 3 | **Jailbreaks** | HIGH | Attempts to bypass safety (DAN, developer mode, roleplay attacks) | Dedicated detection patterns for known jailbreak techniques, system prompt hardening, output filtering as secondary defense | ✅ Implemented |
| 4 | **Data Exfiltration** | HIGH | Queries designed to extract all documents, embeddings, or database contents | Exfiltration guard with 8+ patterns detecting bulk data requests, enumeration attempts, and export requests | ✅ Implemented |
| 5 | **Secret Leakage** | CRITICAL | LLM outputs API keys, credentials, or connection strings found in documents | Output filter scans for 9+ secret patterns (API keys, tokens, passwords, connection strings), blocks entire response on match | ✅ Implemented |
| 6 | **Storage Exposure** | MEDIUM | Blob storage publicly accessible, unauthorized access to documents | Storage: processed entirely in-memory, raw documents discarded, embeddings stored ephemerally | ✅ Implemented |
| 7 | **API Abuse / DoS** | MEDIUM | Excessive requests overwhelming free-tier resources | Rate limiting (10 req/min query, 5 req/min ingest), per-IP tracking, 429 responses with Retry-After | ✅ Implemented |
| 8 | **PII Exposure** | HIGH | Personally identifiable information leaked in logs or responses | PII masker detects emails, phones, credit cards, SSNs. Applied to all log output (global filter) and LLM responses (output filter) | ✅ Implemented |
| 9 | **Unauthorized Access** | HIGH | Unauthenticated or unauthorized API access | API key authentication on all mutation endpoints, constant-time comparison, keys stored securely in Render Environment Variables | ✅ Implemented |
| 10 | **System Prompt Extraction** | MEDIUM | User tricks LLM into revealing its system instructions | System prompt includes explicit "never reveal" instruction, output filter detects leakage patterns | ✅ Implemented |
| 11 | **Hallucination** | MEDIUM | LLM generates factually incorrect answers not grounded in documents | Out-of-scope detection via cosine similarity threshold, system prompt enforces context-only answers, citations required | ✅ Implemented |
| 12 | **Container Escape** | LOW | Attacker exploits container runtime vulnerability | Non-root user in Docker, minimal base image (python:slim), no shell tools in production, read-only filesystem where possible | ✅ Implemented |

## Remaining Risk

### Adversarial Embedding Attacks

**Threat**: A sophisticated attacker could craft document content that is semantically similar to common queries (high cosine similarity) but contains subtly misleading information. This content would bypass the similarity threshold check and be fed to the LLM as relevant context.

**Current Gap**: The system trusts embedding similarity as a proxy for relevance. If an adversary can craft text that embeds close to target queries while containing disinformation, the retrieval system cannot distinguish it from legitimate content.

**Risk Level**: MEDIUM — Requires the attacker to have upload access AND knowledge of the embedding model.

**Future Mitigations**:
1. **Embedding diversity checks**: Flag when retrieved chunks from a single document dominate results.
2. **Cross-referencing**: Require answers to be supported by chunks from multiple independent documents.
3. **Content integrity hashing**: Verify document checksums against an allow-list of trusted uploads.
4. **Human-in-the-loop**: Flag low-confidence answers for manual review before delivery.
