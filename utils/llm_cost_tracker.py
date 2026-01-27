"""
LLM Cost Tracker
Mandatory cost logging for every LLM call
Ensures transparency and cost control
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime
from anthropic import Anthropic

logger = logging.getLogger(__name__)


# Claude 3.5 pricing (as of 2024)
# https://www.anthropic.com/pricing
CLAUDE_PRICING = {
    "claude-3-5-sonnet-20241022": {
        "input": 3.00 / 1_000_000,  # $3 per million input tokens
        "output": 15.00 / 1_000_000,  # $15 per million output tokens
    },
    "claude-3-sonnet-20240229": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
    },
    "claude-3-haiku-20240307": {
        "input": 0.25 / 1_000_000,  # $0.25 per million input tokens
        "output": 1.25 / 1_000_000,  # $1.25 per million output tokens
    },
    # Add more models as needed
}


class LLMCostTracker:
    """
    Tracks LLM API costs with mandatory logging
    """

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.call_count = 0
        self.call_log = []

    def log_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        purpose: str = "unknown"
    ):
        """
        Log an LLM API call with cost calculation

        Args:
            model: Model name (e.g., "claude-3-5-sonnet-20241022")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            purpose: Description of what this call was for
        """
        # Calculate cost
        if model in CLAUDE_PRICING:
            pricing = CLAUDE_PRICING[model]
            input_cost = input_tokens * pricing["input"]
            output_cost = output_tokens * pricing["output"]
            total_cost = input_cost + output_cost
        else:
            logger.warning(f"Unknown model: {model}, using default pricing")
            # Default to Sonnet pricing
            total_cost = (input_tokens * 3.00 / 1_000_000) + (output_tokens * 15.00 / 1_000_000)

        # Update totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += total_cost
        self.call_count += 1

        # Log the call
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "purpose": purpose,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": total_cost
        }
        self.call_log.append(log_entry)

        # MANDATORY: Print cost log
        logger.info(
            f"LLM_CALL | model={model} | purpose={purpose} | "
            f"input_tokens={input_tokens} | output_tokens={output_tokens} | "
            f"cost=${total_cost:.6f}"
        )

    def print_summary(self):
        """
        Print final cost summary
        MUST be called at the end of workflow
        """
        print("\n" + "="*60)
        print("💰 LLM COST SUMMARY")
        print("="*60)
        print(f"Total API calls: {self.call_count}")
        print(f"Total input tokens: {self.total_input_tokens:,}")
        print(f"Total output tokens: {self.total_output_tokens:,}")
        print(f"Total cost: ${self.total_cost_usd:.6f}")
        print("="*60 + "\n")

    def get_summary(self) -> Dict:
        """
        Get cost summary as dict

        Returns:
            Dict with cost metrics
        """
        return {
            "call_count": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "call_log": self.call_log
        }


# Global tracker instance
_cost_tracker = None


def get_cost_tracker() -> LLMCostTracker:
    """Get global cost tracker instance"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = LLMCostTracker()
    return _cost_tracker


def reset_cost_tracker():
    """Reset the global cost tracker"""
    global _cost_tracker
    _cost_tracker = LLMCostTracker()


class ClaudeClient:
    """
    Wrapper around Anthropic Claude API with automatic cost tracking
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude client

        Args:
            api_key: Claude API key (defaults to CLAUDE_KEY env var)
        """
        api_key = api_key or os.getenv("CLAUDE_KEY")
        if not api_key:
            raise ValueError(
                "❌ CLAUDE_KEY not found in environment.\n"
                "Set CLAUDE_KEY in your .env file"
            )

        self.client = Anthropic(api_key=api_key)
        self.cost_tracker = get_cost_tracker()
        logger.info("✅ Claude client initialized with cost tracking")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = "claude-3-haiku-20240307",
        max_tokens: int = 1024,
        temperature: float = 0.0,
        purpose: str = "generation"
    ) -> str:
        """
        Generate text with Claude and track costs

        Args:
            prompt: User prompt
            system: System prompt (optional)
            model: Claude model to use
            max_tokens: Maximum output tokens
            temperature: Sampling temperature (0-1)
            purpose: Description of purpose (for logging)

        Returns:
            Generated text
        """
        logger.info(f"🤖 Calling Claude: {purpose}")

        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }

        if system:
            kwargs["system"] = system

        try:
            response = self.client.messages.create(**kwargs)

            # Extract tokens from usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Log cost
            self.cost_tracker.log_call(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                purpose=purpose
            )

            # Extract text
            return response.content[0].text

        except Exception as e:
            logger.error(f"❌ Error calling Claude: {e}")
            raise


# Convenience function
def get_claude_client() -> ClaudeClient:
    """Get Claude client with cost tracking"""
    return ClaudeClient()


if __name__ == "__main__":
    # Test cost tracker
    tracker = get_cost_tracker()

    # Simulate some API calls
    tracker.log_call("claude-3-haiku-20240307", input_tokens=500, output_tokens=200, purpose="test")
    tracker.log_call("claude-3-5-sonnet-20241022", input_tokens=1000, output_tokens=500, purpose="test")

    # Print summary
    tracker.print_summary()
