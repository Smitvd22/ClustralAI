# =============================================================================
# Test: Out-of-Scope Detection
# =============================================================================
"""
Tests that the system refuses to answer questions that cannot be
answered from the ingested documents.

The system must not hallucinate — it should return the standard
refusal message for out-of-scope queries.
"""
import pytest


class TestOutOfScopeViaAPI:
    """Tests for out-of-scope detection through the API endpoint."""

    @pytest.mark.parametrize("off_topic_question", [
        "What is the capital of France?",
        "Tell me a joke about programming",
        "How do you cook spaghetti carbonara?",
        "What is the meaning of life?",
        "Who won the World Cup in 2022?",
        "Explain quantum computing",
        "What is the weather like today?",
    ])
    def test_refuses_off_topic_questions(
        self,
        client,
        auth_headers: dict,
        off_topic_question: str,
    ) -> None:
        """
        Verify that unrelated questions receive the standard refusal.

        The expected response contains:
        "I cannot answer that based on the provided documents."
        """
        response = client.post(
            "/query",
            json={"question": off_topic_question},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        answer = data["answer"].lower()
        # Accept either the retriever's refusal or the LLM's refusal
        assert (
            "cannot answer" in answer
            or "unable to" in answer
            or "provided documents" in answer
            or "no documents" in answer
        ), f"Expected refusal for off-topic question '{off_topic_question}', got: {data['answer']}"


class TestOutOfScopeRetriever:
    """Tests for the retriever's out-of-scope detection."""

    def test_empty_collection_returns_unanswerable(
        self, temp_vector_store
    ) -> None:
        """When no documents are ingested, all queries should be unanswerable."""
        from rag.retriever import retrieve_relevant_chunks
        from rag.embeddings import embed_query

        query_embedding = embed_query("What is the refund policy?")
        result = retrieve_relevant_chunks(
            vector_store=temp_vector_store,
            query_embedding=query_embedding,
            top_k=3,
        )
        assert not result.is_answerable
        assert len(result.chunks) == 0
