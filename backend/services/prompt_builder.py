def build_prompt(question: str, chunks: list[dict]) -> str:
    """Build a simple prompt from question + retrieved chunks."""
    context = "\n\n".join(
        f"Source: {chunk.get('title', 'Unknown')}\n"
        f"URL: {chunk.get('url', '')}\n"
        f"Content: {chunk.get('snippet') or chunk.get('content', '')}"
        for chunk in chunks
    )

    return f"Answer the question using the provided context.\n\nQuestion: {question}\n\nContext:\n{context}\n"
