# Streaming Stacks vs. Vector Database Integration: Technical Summary

## Core Architecture Patterns
1. **Inline Transformation (CDC → Streaming Agent → Vector DB):** Best for moderate throughput (<1k records/sec). Simplifies infrastructure but ties performance to the embedding API's latency.
2. **Decoupled (CDC → Kafka → Embedding Service → Vector DB):** Ideal for high-throughput, custom embedding logic, and cost-efficient batching. Requires managing more components.

## Vector Database Streaming Profiles
- **Pinecone:** Excellent for zero-ops, serverless scaling, and simple upsert workflows.
- **Weaviate:** Strong choice if you want built-in vectorization and powerful hybrid search capabilities.
- **Qdrant:** High-performance, Rust-backed, with superior filtering and gRPC support.
- **pgvector:** The 'path of least resistance' for PostgreSQL shops. Great for quick deployment but may struggle with extreme scale.
- **Milvus:** Built for massive, distributed scale where storage and compute decoupling is required.