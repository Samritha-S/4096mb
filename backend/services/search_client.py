class SearchClient:
    """Wraps a retrieval/search function and returns document chunks."""

    def search(self, question: str, max_results: int = 5) -> list[dict]:
        """Replace this with your Person 4 search() implementation."""
        return [
            {
                "title": "Example repository note",
                "url": "https://example.com/repo",
                "snippet": "This is an example retrieved chunk.",
                "content": "This is an example retrieved chunk.",
            }
        ][:max_results]
