from __future__ import annotations

from typing import Any


def sample_sections() -> list[dict[str, Any]]:
    return [
        {
            "heading": "What is Retrieval-Augmented Generation?",
            "content": (
                "Retrieval-Augmented Generation, or RAG, is an AI architecture that combines "
                "a document retrieval system with a generative language model. Instead of "
                "relying solely on the model's internal knowledge, RAG first retrieves "
                "relevant documents from a knowledge base and then uses those documents as "
                "context for generating responses. This approach dramatically reduces "
                "hallucinations and improves factual accuracy.\n\n"
                "The key insight behind RAG is that language models are remarkably good at "
                "understanding and summarizing information, but they struggle with recall. "
                "A model like GPT-4o mini might know general facts about a topic, but it "
                "cannot reliably recall specific details from your company's internal "
                "documentation. By providing relevant context at query time, RAG bridges "
                "this gap.\n\n"
                "RAG has become the standard architecture for production AI systems that "
                "need to answer questions based on specific knowledge bases. Major companies "
                "including Google, Microsoft, and Amazon have adopted RAG for their "
                "enterprise AI products. The architecture is particularly valuable for "
                "customer support, internal knowledge management, and research assistance.\n\n"
                "The core workflow involves three stages: indexing, retrieval, and generation. "
                "During indexing, documents are split into chunks, embedded into vectors, "
                "and stored in a vector database. At query time, the user's question is "
                "embedded using the same model, and the vector database returns the most "
                "similar chunks. These chunks are then passed as context to the LLM along "
                "with the original question to generate a grounded response."
            ),
            "word_count": 285,
            "key_points": [
                "RAG combines retrieval with generation for grounded output",
                "Reduces hallucinations by providing relevant context",
                "Three-stage workflow: index, retrieve, generate",
                "Industry standard for enterprise AI applications",
            ],
            "entities": ["RAG", "GPT-4o mini", "Google", "Microsoft", "Amazon"],
            "readability_score": 58.0,
            "metadata": {
                "section_type": "definition",
                "position": 1,
                "word_count": 285,
                "estimated_read_time": "1.4 min",
                "has_code": False,
                "has_statistics": True,
            },
        },
        {
            "heading": "Semantic Chunking Strategies for Better Retrieval",
            "content": (
                "Chunking is the process of splitting documents into smaller pieces for "
                "embedding and retrieval. The quality of your chunking strategy directly "
                "impacts retrieval accuracy. Naive approaches like fixed-size chunking "
                "often split sentences or concepts in half, losing critical context.\n\n"
                "Semantic chunking solves this by respecting natural language boundaries. "
                "Instead of cutting at an arbitrary token count, semantic chunking splits "
                "at paragraph boundaries, sentence endings, or topic transitions. This "
                "ensures each chunk contains a coherent unit of information.\n\n"
                "The RecursiveCharacterTextSplitter from LangChain is the most popular "
                "implementation. It uses a hierarchy of separators starting with double "
                "newlines, then single newlines, then periods, and finally characters. "
                "This approach first tries to split at paragraph boundaries, then "
                "sentences, and only falls back to character-level splitting when necessary.\n\n"
                "Chunk overlap is equally important. Without overlap, a question that "
                "references information spread across a chunk boundary will miss half "
                "the context. A standard configuration uses 512 token chunks with 64 "
                "tokens of overlap, which provides a good balance between granularity "
                "and context preservation.\n\n"
                "The optimal chunk size depends on your use case. For question answering "
                "over technical documentation, 256 to 512 tokens works well. For "
                "summarization tasks, larger chunks of 1024 tokens may be appropriate. "
                "For code retrieval, chunking at function or class boundaries yields "
                "the best results regardless of token count."
            ),
            "word_count": 312,
            "key_points": [
                "Chunking quality directly impacts retrieval accuracy",
                "Semantic chunking respects natural language boundaries",
                "RecursiveCharacterTextSplitter provides hierarchical splitting",
                "Chunk overlap prevents context loss at boundaries",
                "Optimal chunk size varies by use case",
            ],
            "entities": ["RecursiveCharacterTextSplitter", "LangChain"],
            "readability_score": 55.0,
            "metadata": {
                "section_type": "how_to",
                "position": 4,
                "word_count": 312,
                "estimated_read_time": "1.5 min",
                "has_code": True,
                "has_statistics": False,
            },
        },
        {
            "heading": "Production Deployment with Docker and Kubernetes",
            "content": (
                "Deploying a RAG pipeline to production requires careful consideration of "
                "scalability, reliability, and resource management. Each component of the "
                "pipeline has different scaling characteristics and resource requirements, "
                "making containerization with Docker and orchestration with Kubernetes "
                "the ideal deployment strategy.\n\n"
                "Start by containerizing each component separately: the embedding service, "
                "vector database, reranking service, and generation service. Each container "
                "should have its own Dockerfile with optimized base images. Use "
                "Python 3.12 slim images for API services and the official ChromaDB image "
                "for the vector store.\n\n"
                "Kubernetes manifests define how these containers run in production. Each "
                "component gets its own deployment with resource requests and limits. The "
                "embedding service typically needs GPU resources, while the vector database "
                "needs fast SSD storage. Use HorizontalPodAutoscaler to scale each "
                "component independently based on CPU and memory utilization.\n\n"
                "Networking is handled through Kubernetes services. The internal API gateway "
                "routes requests to the appropriate service. Use Istio or Linkerd for "
                "service mesh capabilities including traffic splitting, retry logic, and "
                "circuit breaking.\n\n"
                "For stateful components like ChromaDB, use StatefulSets with persistent "
                "volume claims. Configure readiness and liveness probes for each component "
                "so Kubernetes can automatically restart failed containers. Store sensitive "
                "configuration like API keys in Kubernetes secrets rather than environment "
                "variables in the manifest files."
            ),
            "word_count": 325,
            "key_points": [
                "Containerize each component independently",
                "Use Kubernetes for orchestration and scaling",
                "Configure resource requests and limits per component",
                "Implement service mesh for advanced traffic management",
                "Use StatefulSets for stateful components like vector DBs",
            ],
            "entities": ["Docker", "Kubernetes", "ChromaDB", "Istio", "Linkerd"],
            "readability_score": 52.0,
            "metadata": {
                "section_type": "guide",
                "position": 7,
                "word_count": 325,
                "estimated_read_time": "1.6 min",
                "has_code": True,
                "has_statistics": False,
            },
        },
        {
            "heading": "Monitoring and Observability with Prometheus and Grafana",
            "content": (
                "Production RAG pipelines require comprehensive monitoring to ensure "
                "reliability and performance. Without observability, you are flying blind. "
                "Every component of the pipeline should expose metrics, and those metrics "
                "should be aggregated, visualized, and alerted upon.\n\n"
                "Prometheus serves as the metrics collection and storage layer. Each "
                "service exposes a /metrics endpoint that Prometheus scrapes at regular "
                "intervals. Key metrics include request latency histograms, error rates, "
                "queue depths, and cache hit ratios. Use separate histograms for each "
                "pipeline stage to identify bottlenecks.\n\n"
                "Grafana provides visualization and dashboards. A well-designed monitoring "
                "dashboard includes panels for end-to-end latency broken down by stage, "
                "retrieval quality metrics like hit rate and MRR, error rates by component, "
                "resource utilization for each container, and cache performance metrics.\n\n"
                "Alerting is critical for production systems. Set up alerts for P95 "
                "latency exceeding 2 seconds, error rates above 1 percent, cache hit "
                "rate dropping below 40 percent, and any component reporting unhealthy "
                "status. Use Alertmanager to route alerts to PagerDuty, Slack, or email.\n\n"
                "Distributed tracing with OpenTelemetry provides visibility into individual "
                "requests as they flow through the pipeline. This is invaluable for "
                "debugging performance issues and identifying which stage is responsible "
                "for latency spikes. Instrument each service with OpenTelemetry SDK and "
                "export traces to Jaeger or Tempo."
            ),
            "word_count": 308,
            "key_points": [
                "Every component must expose metrics for observability",
                "Prometheus collects metrics, Grafana visualizes them",
                "Track latency histograms per pipeline stage",
                "Set up alerts for critical threshold violations",
                "Distributed tracing enables end-to-end request visibility",
            ],
            "entities": ["Prometheus", "Grafana", "OpenTelemetry", "Jaeger", "Tempo"],
            "readability_score": 50.0,
            "metadata": {
                "section_type": "guide",
                "position": 8,
                "word_count": 308,
                "estimated_read_time": "1.5 min",
                "has_code": False,
                "has_statistics": True,
            },
        },
        {
            "heading": "Implementing Query Rewriting for Improved Accuracy",
            "content": (
                "Query rewriting is a powerful optimization technique that significantly "
                "improves retrieval quality. The core idea is simple: before sending a "
                "user's question to the retrieval system, use an LLM to rewrite it into "
                "a more effective search query. This addresses several common problems "
                "with user queries.\n\n"
                "Users often ask vague questions like tell me about it without specifying "
                "what it refers to. Query rewriting resolves these ambiguities by "
                "incorporating conversation history and context. It also handles cases "
                "where the user's natural language question doesn't match the vocabulary "
                "used in the target documents.\n\n"
                "The implementation uses a carefully crafted prompt template. The LLM "
                "receives the conversation history, the current question, and instructions "
                "to generate a standalone search query. The temperature is set to 0 for "
                "deterministic output, and the response is constrained to a single sentence "
                "that captures the core information need.\n\n"
                "Our benchmarks show that query rewriting improves hit rate from 0.82 to "
                "0.94, a 15 percent relative improvement. The overhead is minimal since "
                "the rewriting uses a small, fast model like GPT-4o mini with a 50-token "
                "output limit, typically completing in under 100 milliseconds.\n\n"
                "One important consideration is when to rewrite. For simple factual queries "
                "where the user's wording already matches document vocabulary, rewriting "
                "may not help. Implement a classifier that decides whether rewriting is "
                "needed based on query length, ambiguity score, and conversation context."
            ),
            "word_count": 295,
            "key_points": [
                "Query rewriting resolves ambiguous and vague queries",
                "Uses LLM to generate standalone search queries from context",
                "Improves hit rate by 15 percent in benchmark tests",
                "Minimal latency overhead with small fast models",
                "Selective rewriting avoids unnecessary processing",
            ],
            "entities": ["GPT-4o mini"],
            "readability_score": 54.0,
            "metadata": {
                "section_type": "tutorial",
                "position": 5,
                "word_count": 295,
                "estimated_read_time": "1.4 min",
                "has_code": True,
                "has_statistics": True,
            },
        },
    ]


def sample_section_content() -> str:
    return (
        "Semantic chunking is the most critical preprocessing step in any RAG pipeline. "
        "The quality of your chunks directly determines the ceiling on retrieval accuracy. "
        "Poorly chunked documents will produce poor results regardless of how good your "
        "embedding model or vector database is.\n\n"
        "The fundamental problem with naive chunking is that it destroys context. When you "
        "split a document at a fixed token count, you inevitably cut through sentences, "
        "paragraphs, and even words. A question that needs information from both sides of "
        "a split boundary will only receive half the context.\n\n"
        "Semantic chunking solves this by splitting at natural language boundaries. The "
        "algorithm works hierarchically. It first tries to split at major section breaks "
        "indicated by markdown headings or HTML tags. If those are absent, it splits at "
        "paragraph boundaries marked by double newlines. Next, it tries sentence boundaries "
        "at periods, question marks, and exclamation points. Only as a last resort does it "
        "fall back to character-level splitting.\n\n"
        "Here is the recommended configuration for production systems:\n\n"
        "Chunk size: 512 tokens\n"
        "Chunk overlap: 64 tokens\n"
        "Separators: ['\\n\\n', '\\n', '.', '?', '!', ' ', '']\n"
        "Length function: token count via tiktoken\n\n"
        "The 64-token overlap ensures that information near chunk boundaries appears in "
        "two chunks. This means a question referencing information that spans a boundary "
        "will still find the complete context in one of the overlapping chunks.\n\n"
        "For code documentation, consider chunking at function or class boundaries. "
        "Parse the source code into an AST and use that structure for splitting. This "
        "approach preserves the logical coherence of code blocks and ensures that "
        "function signatures remain with their documentation strings.\n\n"
        "Evaluate your chunking strategy by measuring retrieval metrics on a held-out "
        "test set. Track hit rate at different K values, mean reciprocal rank, and the "
        "percentage of queries where the top result contains the answer. These metrics "
        "will guide your chunking optimization decisions."
    )


def sample_section_metadata() -> dict[str, Any]:
    return {
        "section_type": "body",
        "position": 4,
        "word_count": 425,
        "estimated_read_time": "2.1 min",
        "has_code": True,
        "has_table": False,
        "has_image": False,
        "has_statistics": True,
        "has_callout": False,
        "keyword_density": 0.028,
        "readability_score": 53.5,
        "heading_tag": "h2",
    }
