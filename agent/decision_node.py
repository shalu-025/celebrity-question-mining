"""
Decision Agent Node
LLM-based decision making for INGEST vs RETRIEVE
This is the "agentic" layer that decides the workflow path

🔴 UPDATED: Now uses Claude API (not OpenAI) with cost tracking
"""

import os
import json
from typing import Dict, Literal, Optional, List
from datetime import datetime
from utils.logger import get_logger
from utils.llm_cost_tracker import get_claude_client, get_cost_tracker

logger = get_logger(__name__)


DecisionType = Literal["INGEST", "RETRIEVE", "INCREMENTAL_INGEST"]


class DecisionAgent:
    """
    Agentic decision maker using LLM
    Analyzes registry and context to decide workflow path
    """

    def __init__(
        self,
        registry_path: str = "registry/celebrity_index.json"
    ):
        """
        Initialize Decision Agent with Claude API

        🔴 CRITICAL: Uses Claude (not OpenAI) with cost tracking
        """
        self.registry_path = registry_path
        self.client = get_claude_client()
        self.cost_tracker = get_cost_tracker()
        logger.info("✅ Decision Agent initialized (Claude API with cost tracking)")

    def load_registry(self) -> Dict:
        """Load celebrity registry"""
        if not os.path.exists(self.registry_path):
            logger.warning("Registry not found, creating new one")
            return {"celebrities": {}, "last_updated": None, "version": "1.0.0"}

        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {"celebrities": {}, "last_updated": None, "version": "1.0.0"}

    def save_registry(self, registry: Dict):
        """Save celebrity registry"""
        try:
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            with open(self.registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
            logger.info("Registry saved")
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
            raise

    def get_celebrity_status(self, celebrity_name: str) -> Optional[Dict]:
        """Get indexing status for a celebrity"""
        registry = self.load_registry()
        return registry['celebrities'].get(celebrity_name)

    def make_decision(
        self,
        celebrity_name: str,
        user_question: str,
        force_ingest: bool = False
    ) -> Dict:
        """
        Make agentic decision using LLM

        Args:
            celebrity_name: Name of the celebrity
            user_question: User's question
            force_ingest: Force ingestion even if data exists

        Returns:
            Dict containing:
                - decision: "INGEST", "RETRIEVE", or "INCREMENTAL_INGEST"
                - reasoning: Explanation of the decision
                - celebrity_status: Current status of the celebrity in registry
        """
        logger.info(f"Making decision for: {celebrity_name}")

        # Load registry
        registry = self.load_registry()
        celebrity_status = registry['celebrities'].get(celebrity_name)

        # If force ingest, skip LLM decision
        if force_ingest:
            return {
                "decision": "INGEST",
                "reasoning": "Force ingest requested by user",
                "celebrity_status": celebrity_status
            }

        # Build context for LLM
        if celebrity_status is None:
            status_text = f"{celebrity_name} has NEVER been indexed."
        else:
            status_text = f"""{celebrity_name} was indexed on {celebrity_status['last_indexed']}.
Sources indexed: {celebrity_status['sources_count']} ({', '.join(celebrity_status['source_types'])})
Questions indexed: {celebrity_status['questions_count']}
Last update: {celebrity_status['last_updated']}"""

        # Create decision prompt
        prompt = f"""You are a decision agent for an interview question retrieval system.

CONTEXT:
- User is asking: "{user_question}"
- Celebrity: {celebrity_name}

CURRENT STATUS:
{status_text}

YOUR TASK:
Decide whether to:
1. "INGEST" - Index new data for this celebrity (download and process interviews)
2. "RETRIEVE" - Search existing indexed data
3. "INCREMENTAL_INGEST" - Add new sources to existing index

DECISION RULES:
- If celebrity is NOT indexed → INGEST
- If celebrity IS indexed and data is recent (within 30 days) → RETRIEVE
- If celebrity IS indexed but data is old (>30 days) → INCREMENTAL_INGEST (add new sources)
- If celebrity IS indexed but has very few sources (<3) → INCREMENTAL_INGEST

Respond in JSON format:
{{
    "decision": "INGEST" | "RETRIEVE" | "INCREMENTAL_INGEST",
    "reasoning": "Brief explanation of why this decision was made"
}}"""

        try:
            response_text = self.client.generate(
                prompt=prompt + "\n\nRespond with ONLY a JSON object, no other text.",
                system="You are a precise decision-making agent. Always respond with valid JSON.",
                model="claude-sonnet-4-20250514",  # ✅ Per requirements
                max_tokens=200,
                temperature=0,
                purpose="agent_decision_making"
            )

            # Parse JSON from response
            result = json.loads(response_text)
            decision = result['decision']
            reasoning = result['reasoning']

            logger.info(f"Decision: {decision}")
            logger.info(f"Reasoning: {reasoning}")

            return {
                "decision": decision,
                "reasoning": reasoning,
                "celebrity_status": celebrity_status
            }

        except Exception as e:
            logger.error(f"Error in LLM decision: {e}")

            # Fallback to simple logic
            if celebrity_status is None:
                return {
                    "decision": "INGEST",
                    "reasoning": "Fallback: Celebrity not indexed",
                    "celebrity_status": None
                }
            else:
                return {
                    "decision": "RETRIEVE",
                    "reasoning": "Fallback: Celebrity already indexed",
                    "celebrity_status": celebrity_status
                }

    def update_registry_after_ingest(
        self,
        celebrity_name: str,
        sources_ingested: List[str],
        questions_count: int,
        source_types: List[str]
    ):
        """
        Update registry after ingestion

        Args:
            celebrity_name: Name of the celebrity
            sources_ingested: List of source URLs ingested
            questions_count: Number of questions extracted
            source_types: List of source types (youtube, podcast, article)
        """
        registry = self.load_registry()

        celebrity_data = {
            "last_indexed": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "sources_count": len(sources_ingested),
            "questions_count": questions_count,
            "source_types": list(set(source_types)),
            "sources": sources_ingested
        }

        registry['celebrities'][celebrity_name] = celebrity_data
        registry['last_updated'] = datetime.utcnow().isoformat()

        self.save_registry(registry)
        logger.info(f"Registry updated for {celebrity_name}")

    def update_registry_after_incremental(
        self,
        celebrity_name: str,
        new_sources: List[str],
        new_questions_count: int,
        new_source_types: List[str]
    ):
        """
        Update registry after incremental ingestion

        Args:
            celebrity_name: Name of the celebrity
            new_sources: List of new source URLs
            new_questions_count: Number of new questions extracted
            new_source_types: List of new source types
        """
        registry = self.load_registry()

        if celebrity_name not in registry['celebrities']:
            logger.error(f"Celebrity {celebrity_name} not in registry for incremental update")
            return

        celebrity_data = registry['celebrities'][celebrity_name]

        # Update counts
        celebrity_data['sources_count'] += len(new_sources)
        celebrity_data['questions_count'] += new_questions_count
        celebrity_data['last_updated'] = datetime.utcnow().isoformat()

        # Merge source types
        existing_types = set(celebrity_data.get('source_types', []))
        celebrity_data['source_types'] = list(existing_types.union(set(new_source_types)))

        # Merge sources
        existing_sources = celebrity_data.get('sources', [])
        celebrity_data['sources'] = existing_sources + new_sources

        registry['celebrities'][celebrity_name] = celebrity_data
        registry['last_updated'] = datetime.utcnow().isoformat()

        self.save_registry(registry)
        logger.info(f"Registry incrementally updated for {celebrity_name}")


if __name__ == "__main__":
    # Test decision agent
    agent = DecisionAgent(registry_path="registry/celebrity_index.json")

    # Test decision for non-existent celebrity
    result = agent.make_decision("New Celebrity", "What inspired you?")
    print("\n=== Decision for New Celebrity ===")
    print(f"Decision: {result['decision']}")
    print(f"Reasoning: {result['reasoning']}")

    # Simulate updating registry
    agent.update_registry_after_ingest(
        "New Celebrity",
        sources_ingested=["url1", "url2", "url3"],
        questions_count=50,
        source_types=["youtube", "podcast"]
    )

    # Test decision for existing celebrity
    result = agent.make_decision("New Celebrity", "What's your favorite role?")
    print("\n=== Decision for Existing Celebrity ===")
    print(f"Decision: {result['decision']}")
    print(f"Reasoning: {result['reasoning']}")
