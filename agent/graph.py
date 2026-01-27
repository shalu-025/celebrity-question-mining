"""
LangGraph State Machine
Orchestrates the agentic workflow: Decision → Ingest/Retrieve → Answer
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal, List, Dict, Optional
import logging
import json
import os
from agent.decision_node import DecisionAgent
from ingestion.youtube_ingest import YouTubeIngester
from ingestion.podcast_ingest import PodcastIngester
from ingestion.article_ingest import ArticleIngester
from retrieval.search import QuestionRetriever
from llm.answer_generator import AnswerGenerator
from embeddings.embedder import get_embedder
from vector_db.faiss_index import FAISSIndexManager
from vector_db.metadata_store import MetadataStore
from processing.semantic_chunker import get_semantic_chunker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """State shared across all nodes"""
    # Input
    celebrity_name: str
    user_question: str
    force_ingest: bool

    # Decision
    decision: Optional[str]
    decision_reasoning: Optional[str]

    # Ingestion
    ingested_questions: Optional[List[Dict]]
    ingestion_success: bool

    # Retrieval
    retrieval_results: Optional[Dict]

    # Output
    final_answer: Optional[str]
    error: Optional[str]


class CelebrityQuestionGraph:
    """
    LangGraph-based agentic workflow
    Routes between ingestion and retrieval based on Decision Agent
    """

    def __init__(self):
        # Initialize all components
        self.decision_agent = DecisionAgent()
        self.youtube_ingester = YouTubeIngester()
        self.podcast_ingester = PodcastIngester()
        self.article_ingester = ArticleIngester()
        self.retriever = QuestionRetriever(similarity_threshold=0.50)
        self.answer_generator = AnswerGenerator()
        self.embedder = get_embedder()
        self.faiss_manager = FAISSIndexManager()
        self.metadata_store = MetadataStore()
        self.semantic_chunker = get_semantic_chunker()

        # Load sources configuration
        self.sources_config = self._load_sources_config()

        # Build graph
        self.graph = self._build_graph()
        logger.info("Celebrity Question Graph initialized")

    def _load_sources_config(self) -> Dict:
        """Load celebrity sources configuration from JSON file"""
        config_path = "config/celebrity_sources.json"

        if not os.path.exists(config_path):
            logger.warning(f"Sources config not found at {config_path}, using empty config")
            return {"celebrities": {}, "default_podcast_feeds": []}

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded sources config for {len(config.get('celebrities', {}))} celebrities")
                return config
        except Exception as e:
            logger.error(f"Error loading sources config: {e}")
            return {"celebrities": {}, "default_podcast_feeds": []}

    def _get_celebrity_sources(self, celebrity_name: str) -> Dict:
        """Get podcast feeds and article URLs for a specific celebrity"""
        celebrities = self.sources_config.get("celebrities", {})

        # Try exact match first
        if celebrity_name in celebrities:
            return celebrities[celebrity_name]

        # Try case-insensitive match
        for name, sources in celebrities.items():
            if name.lower() == celebrity_name.lower():
                return sources

        # Return default/empty if not found
        return {
            "podcast_feeds": self.sources_config.get("default_podcast_feeds", []),
            "article_urls": []
        }

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""

        # Create graph
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("decision", self.decision_node)
        workflow.add_node("ingest", self.ingest_node)
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("generate_answer", self.generate_answer_node)

        # Set entry point
        workflow.set_entry_point("decision")

        # Add conditional edges from decision node
        workflow.add_conditional_edges(
            "decision",
            self.route_after_decision,
            {
                "ingest": "ingest",
                "retrieve": "retrieve"
            }
        )

        # After ingestion, go to retrieval
        workflow.add_edge("ingest", "retrieve")

        # After retrieval, generate answer
        workflow.add_edge("retrieve", "generate_answer")

        # After answer generation, end
        workflow.add_edge("generate_answer", END)

        return workflow.compile()

    def decision_node(self, state: GraphState) -> GraphState:
        """Decision Agent Node - decides INGEST or RETRIEVE"""
        logger.info("=== DECISION NODE ===")

        try:
            result = self.decision_agent.make_decision(
                state['celebrity_name'],
                state['user_question'],
                state.get('force_ingest', False)
            )

            # Map INCREMENTAL_INGEST to INGEST for now
            decision = result['decision']
            if decision == "INCREMENTAL_INGEST":
                decision = "INGEST"

            state['decision'] = decision
            state['decision_reasoning'] = result['reasoning']

            logger.info(f"Decision: {decision}")
            logger.info(f"Reasoning: {result['reasoning']}")

        except Exception as e:
            logger.error(f"Error in decision node: {e}")
            state['error'] = str(e)
            state['decision'] = "retrieve"  # Fallback to retrieve

        return state

    def route_after_decision(self, state: GraphState) -> Literal["ingest", "retrieve"]:
        """Route to next node based on decision"""
        decision = state.get('decision', 'retrieve').upper()

        if decision == "INGEST":
            return "ingest"
        else:
            return "retrieve"

    def ingest_node(self, state: GraphState) -> GraphState:
        """Ingestion Node - downloads and processes interviews"""
        logger.info("=== INGESTION NODE ===")

        celebrity_name = state['celebrity_name']

        try:
            # Get configured sources for this celebrity
            sources = self._get_celebrity_sources(celebrity_name)

            # Ingest from multiple sources
            all_questions = []

            # 1. YouTube
            logger.info("Ingesting from YouTube...")
            youtube_questions = self.youtube_ingester.ingest_celebrity(
                celebrity_name,
                max_videos=10
            )
            all_questions.extend(youtube_questions)
            logger.info(f"YouTube: Extracted {len(youtube_questions)} questions")

            # 2. Podcasts (if feeds available)
            podcast_feeds = sources.get("podcast_feeds", [])
            if podcast_feeds:
                logger.info(f"Ingesting from Podcasts... ({len(podcast_feeds)} feeds)")
                try:
                    podcast_questions = self.podcast_ingester.ingest_from_feeds(
                        celebrity_name,
                        rss_feeds=podcast_feeds,
                        max_episodes=5
                    )
                    all_questions.extend(podcast_questions)
                    logger.info(f"Podcasts: Extracted {len(podcast_questions)} questions")
                except Exception as e:
                    logger.error(f"Error ingesting podcasts: {e}")
            else:
                logger.info("No podcast feeds configured for this celebrity")

            # In the ingest_node method, replace the article section with:

            # 3. Articles (automatic search if no URLs provided)
            article_urls = sources.get("article_urls", [])

            if article_urls:
                # Use provided URLs
                logger.info(f"Ingesting from Articles... ({len(article_urls)} URLs provided)")
                try:
                    article_questions = self.article_ingester.ingest_from_urls(
                        celebrity_name,
                        article_urls
                    )
                    all_questions.extend(article_questions)
                    logger.info(f"Articles: Extracted {len(article_questions)} questions")
                except Exception as e:
                    logger.error(f"Error ingesting articles: {e}")
            else:
                # Automatic search
                logger.info("No article URLs provided - using automatic search")
                try:
                    article_questions = self.article_ingester.ingest_with_search(
                        celebrity_name,
                        max_articles=5
                    )
                    all_questions.extend(article_questions)
                    logger.info(f"Articles: Extracted {len(article_questions)} questions")
                except Exception as e:
                    logger.error(f"Error searching/ingesting articles: {e}")

            if not all_questions:
                logger.warning("No questions extracted during ingestion")
                state['ingestion_success'] = False
                state['ingested_questions'] = []
                return state

            # DEDUPLICATION DISABLED - Store all questions with their individual sources
            # Even if questions are similar, we keep them separate to preserve all source information
            logger.info(f"Storing {len(all_questions)} questions (deduplication disabled)")

            # Note: Previously deduplicated questions here, but now we keep all raw data
            # This allows retrieval to show multiple sources for similar questions

            # Index questions in FAISS + metadata store
            self._index_questions(celebrity_name, all_questions)

            # Update registry
            source_types = list(set([q['source_type'] for q in all_questions]))
            source_urls = list(set([q['source_url'] for q in all_questions]))

            self.decision_agent.update_registry_after_ingest(
                celebrity_name,
                sources_ingested=source_urls,
                questions_count=len(all_questions),
                source_types=source_types
            )

            state['ingested_questions'] = all_questions
            state['ingestion_success'] = True

            logger.info(f"Ingestion complete: {len(all_questions)} questions indexed (all sources preserved)")

        except Exception as e:
            logger.error(f"Error in ingestion node: {e}")
            state['error'] = str(e)
            state['ingestion_success'] = False

        return state

    def _index_questions(self, celebrity_name: str, questions: List[Dict]):
        """Index questions in FAISS and metadata store"""
        logger.info(f"Indexing {len(questions)} questions for {celebrity_name}")

        # Create or load index
        if not self.faiss_manager.load_index(celebrity_name):
            self.faiss_manager.create_index(celebrity_name, embedding_dim=384)

        # Load metadata store
        self.metadata_store.load_metadata(celebrity_name)

        # Extract question texts
        question_texts = [q['text'] for q in questions]

        # Generate embeddings
        embeddings = self.embedder.embed_batch(question_texts, show_progress=True)

        # Add to FAISS
        faiss_ids = self.faiss_manager.add_vectors(celebrity_name, embeddings)

        # Prepare metadata
        metadata_list = []
        for q in questions:
            metadata_list.append({
                'source_type': q.get('source_type'),
                'source_url': q.get('source_url'),
                'source_title': q.get('source_title'),
                'timestamp': q.get('timestamp'),
                'date': q.get('date')
            })

        # Add metadata
        self.metadata_store.add_metadata(
            celebrity_name,
            faiss_ids,
            question_texts,
            metadata_list
        )

        # Save both
        self.faiss_manager.save_index(celebrity_name)
        self.metadata_store.save_metadata(celebrity_name)

        logger.info(f"Indexed {len(questions)} questions")

    def retrieve_node(self, state: GraphState) -> GraphState:
        """Retrieval Node - searches for similar questions"""
        logger.info("=== RETRIEVAL NODE ===")

        try:
            results = self.retriever.retrieve_with_context(
                state['celebrity_name'],
                state['user_question']
            )

            state['retrieval_results'] = results

            logger.info(f"Retrieved {results['count']} matches")

        except Exception as e:
            logger.error(f"Error in retrieval node: {e}")
            state['error'] = str(e)
            state['retrieval_results'] = {
                'matches': [],
                'count': 0,
                'query': state['user_question'],
                'celebrity': state['celebrity_name']
            }

        return state

    def generate_answer_node(self, state: GraphState) -> GraphState:
        """Answer Generation Node - formats results"""
        logger.info("=== ANSWER GENERATION NODE ===")

        try:
            retrieval_results = state['retrieval_results']

            # Generate natural language answer
            answer = self.answer_generator.generate_natural_response(
                retrieval_results,
                include_insights=True
            )

            state['final_answer'] = answer

            logger.info("Answer generated successfully")

        except Exception as e:
            logger.error(f"Error in answer generation node: {e}")
            state['error'] = str(e)
            state['final_answer'] = "An error occurred while generating the answer."

        return state

    def run(
        self,
        celebrity_name: str,
        user_question: str,
        force_ingest: bool = False
    ) -> Dict:
        """
        Run the full agentic workflow

        Args:
            celebrity_name: Name of the celebrity
            user_question: User's question
            force_ingest: Force ingestion even if data exists

        Returns:
            Dict with final answer and metadata
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting workflow for: {celebrity_name}")
        logger.info(f"Question: {user_question}")
        logger.info(f"{'='*60}\n")

        # Initialize state
        initial_state: GraphState = {
            'celebrity_name': celebrity_name,
            'user_question': user_question,
            'force_ingest': force_ingest,
            'decision': None,
            'decision_reasoning': None,
            'ingested_questions': None,
            'ingestion_success': False,
            'retrieval_results': None,
            'final_answer': None,
            'error': None
        }

        # Run graph
        final_state = self.graph.invoke(initial_state)

        # Return result
        return {
            'answer': final_state.get('final_answer'),
            'decision': final_state.get('decision'),
            'decision_reasoning': final_state.get('decision_reasoning'),
            'matches_count': final_state.get('retrieval_results', {}).get('count', 0),
            'error': final_state.get('error')
        }


if __name__ == "__main__":
    # Test the graph
    graph = CelebrityQuestionGraph()

    # Test run
    result = graph.run(
        celebrity_name="Keanu Reeves",
        user_question="What inspired you to become an actor?",
        force_ingest=False
    )

    print("\n=== RESULT ===")
    print(f"Decision: {result['decision']}")
    print(f"Reasoning: {result['decision_reasoning']}")
    print(f"Matches: {result['matches_count']}")
    print(f"\nAnswer:\n{result['answer']}")
