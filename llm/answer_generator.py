"""
Answer Generator
Formats retrieval results into natural language responses
Uses LLM ONLY for explanation and formatting, NOT for inventing answers

🔄 UPDATED: Now uses Qwen 2.5 3B Instruct via Ollama (OpenAI-compatible API)
"""

import os
from typing import List, Dict, Optional
from utils.logger import get_logger
from utils.llm_cost_tracker import get_claude_client, get_cost_tracker

logger = get_logger(__name__)


class AnswerGenerator:
    """
    Generates natural language answers from retrieved questions
    LLM is used ONLY for formatting, NOT for content generation
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize answer generator with Qwen LLM

        🔄 UPDATED: Uses Qwen 2.5 3B Instruct via Ollama with cost tracking
        """
        self.client = get_claude_client()
        self.cost_tracker = get_cost_tracker()
        logger.info("✅ Answer generator initialized (Qwen LLM with cost tracking)")

    def format_simple_response(self, retrieval_result: Dict) -> str:
        """
        Format retrieval results as simple text (no LLM)

        Args:
            retrieval_result: Dict from QuestionRetriever.retrieve_with_context()

        Returns:
            Formatted string response
        """
        matches = retrieval_result['matches']
        count = retrieval_result['count']
        query = retrieval_result['query']
        celebrity = retrieval_result['celebrity']

        if count == 0:
            return f"No interviews found where {celebrity} was asked a similar question."

        response = f"Found {count} interview{'s' if count > 1 else ''} where {celebrity} was asked this question:\n\n"

        for idx, match in enumerate(matches, 1):
            response += f"{idx}. \"{match['question_text']}\"\n"
            response += f"   Source: {match['source_title']}\n"
            response += f"   Type: {match['source_type'].capitalize()}\n"
            if match['date']:
                response += f"   Date: {match['date']}\n"
            response += f"   Link: {match['source_url']}\n"
            response += f"   Similarity: {match['similarity_score']:.2%}\n\n"

        return response

    def generate_natural_response(
        self,
        retrieval_result: Dict,
        include_insights: bool = True
    ) -> str:
        """
        Generate natural language response using LLM
        LLM formats the results but does NOT invent content

        Args:
            retrieval_result: Dict from QuestionRetriever.retrieve_with_context()
            include_insights: Whether to include analysis/insights

        Returns:
            Natural language response
        """
        matches = retrieval_result['matches']
        count = retrieval_result['count']
        query = retrieval_result['query']
        celebrity = retrieval_result['celebrity']

        if count == 0:
            # No matches - return simple message
            return self._generate_no_results_message(celebrity, query)

        # Build context for LLM
        matches_text = ""
        for idx, match in enumerate(matches, 1):
            matches_text += f"\nMatch {idx}:\n"
            matches_text += f"Question: {match['question_text']}\n"
            matches_text += f"Source: {match['source_title']} ({match['source_type']})\n"
            matches_text += f"Date: {match.get('date', 'Unknown')}\n"
            matches_text += f"URL: {match['source_url']}\n"
            matches_text += f"Similarity: {match['similarity_score']:.2%}\n"

        # Create prompt
        prompt = f"""You are a helpful assistant that presents interview question search results.

User Query: "{query}"
Celebrity: {celebrity}
Number of Matches: {count}

Matching Questions Found:
{matches_text}

Instructions:
1. Summarize that we found {count} interview{'s' if count > 1 else ''} where {celebrity} was asked similar questions
2. For each match, present:
   - The exact question asked
   - Source information (title, type, date)
   - Clickable link
3. {"If multiple sources, note any interesting patterns (e.g., commonly asked, asked at different times)" if include_insights and count > 1 else ""}
4. DO NOT invent answers or information not provided
5. DO NOT speculate about what the celebrity might have said
6. Keep response concise and well-formatted

Format the response in a clear, user-friendly way with proper markdown formatting."""

        try:
            answer = self.client.generate(
                prompt=prompt,
                system="You are a precise assistant that presents search results without adding information.",
                max_tokens=1000,
                temperature=0.3,
                purpose="format_retrieval_results"
            )

            logger.info("Generated natural language response")
            return answer

        except Exception as e:
            logger.error(f"Error generating Qwen LLM response: {e}")
            # Fallback to simple response
            return self.format_simple_response(retrieval_result)

    def _generate_no_results_message(
        self,
        celebrity: str,
        query: str
    ) -> str:
        """Generate a helpful message when no results found"""

        prompt = f"""User asked: "{query}"
Celebrity: {celebrity}

No matching interviews were found in our database where {celebrity} was asked this specific question.

Generate a brief, helpful message (2-3 sentences) that:
1. Politely states that this question wasn't found in our indexed interviews
2. Suggests that the question may not have been asked in available interviews, or we haven't indexed those sources yet
3. Offers that the user could try rephrasing or asking a related question

Keep it concise and friendly."""

        try:
            response = self.client.generate(
                prompt=prompt,
                system="You are a helpful assistant.",
                max_tokens=150,
                temperature=0.5,
                purpose="generate_no_results_message"
            )

            return response

        except Exception as e:
            logger.error(f"Error generating no-results message: {e}")
            return f"No interviews found where {celebrity} was asked a similar question. Try rephrasing your question or asking something related."

    def generate_summary(self, retrieval_result: Dict) -> Dict:
        """
        Generate a structured summary of results

        Returns:
            Dict with summary statistics and insights
        """
        matches = retrieval_result['matches']
        count = retrieval_result['count']

        if count == 0:
            return {
                'total_matches': 0,
                'message': 'No matches found'
            }

        # Group by source type
        source_types = {}
        dates = []
        avg_similarity = 0

        for match in matches:
            source_type = match['source_type']
            source_types[source_type] = source_types.get(source_type, 0) + 1

            if match['date']:
                dates.append(match['date'])

            avg_similarity += match['similarity_score']

        avg_similarity /= count

        return {
            'total_matches': count,
            'average_similarity': avg_similarity,
            'source_types': source_types,
            'date_range': {
                'earliest': min(dates) if dates else None,
                'latest': max(dates) if dates else None
            },
            'top_match_similarity': matches[0]['similarity_score']
        }


if __name__ == "__main__":
    # Test answer generator
    generator = AnswerGenerator()

    # Mock retrieval result
    mock_result = {
        'matches': [
            {
                'question_text': 'What inspired you to become an actor?',
                'source_type': 'youtube',
                'source_title': 'Interview with John Doe',
                'source_url': 'https://youtube.com/watch?v=test',
                'date': '2024-01-15',
                'similarity_score': 0.92
            },
            {
                'question_text': 'Why did you choose acting as a career?',
                'source_type': 'podcast',
                'source_title': 'Podcast Episode 42',
                'source_url': 'https://podcast.com/ep42',
                'date': '2024-02-20',
                'similarity_score': 0.87
            }
        ],
        'count': 2,
        'query': 'What made you want to be an actor?',
        'celebrity': 'Test Celebrity'
    }

    # Test simple format
    print("=== Simple Response ===")
    simple = generator.format_simple_response(mock_result)
    print(simple)

    # Test summary
    print("\n=== Summary ===")
    summary = generator.generate_summary(mock_result)
    print(summary)
