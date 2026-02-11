# RAG Runtime Checks

The RAG agent performs startup fail-fast checks for embedding compatibility before serving traffic.

## Checks Performed
- Probe embedding vector is non-empty, finite, and non-zero norm.
- Probe dimension matches Neo4j vector indexes.
- Probe metadata is compared to `__EmbeddingConfig__` active config.

## Remediation
1. Align embedding deployment/model between ingestion and agent runtime.
2. Rebuild vector indexes if dimensions differ.
3. Re-run ingestion for consistent embeddings.
