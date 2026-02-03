"""
LLM Cost Tracker
Mandatory cost logging for every LLM call
Ensures transparency and cost control

🔄 UPDATED: Now uses Qwen 2.5 3B Instruct via OpenAI-compatible API (e.g., Ollama)
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)


# Default model configuration
DEFAULT_MODEL = os.getenv("QWEN_MODEL", "qwen2.5:3b-instruct")
DEFAULT_BASE_URL = os.getenv("QWEN_BASE_URL", "http://localhost:11434/v1")

# LLM pricing (local models are free, but we track for consistency)
LLM_PRICING = {
    # Qwen models (local - $0 cost)
    "qwen2.5:3b-instruct": {
        "input": 0.0,
        "output": 0.0,
    },
    "qwen2.5-3b-instruct": {
        "input": 0.0,
        "output": 0.0,
    },
    # Legacy Claude pricing (kept for reference)
    "claude-sonnet-4-20250514": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
    },
    "claude-3-5-sonnet-20241022": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
    },
    "claude-3-sonnet-20240229": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
    },
    "claude-3-haiku-20240307": {
        "input": 0.25 / 1_000_000,
        "output": 1.25 / 1_000_000,
    },
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
        if model in LLM_PRICING:
            pricing = LLM_PRICING[model]
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
    Wrapper around OpenAI-compatible API (Qwen via Ollama) with automatic cost tracking

    🔄 UPDATED: Now uses Qwen 2.5 3B Instruct instead of Claude
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize LLM client for Qwen model

        Args:
            api_key: API key (optional for local Ollama, defaults to "ollama")
            base_url: Base URL for OpenAI-compatible API (defaults to Ollama)
        """
        # For Ollama, api_key can be anything (it's not used)
        api_key = api_key or os.getenv("QWEN_API_KEY", "ollama")
        base_url = base_url or os.getenv("QWEN_BASE_URL", DEFAULT_BASE_URL)

        self.model = os.getenv("QWEN_MODEL", DEFAULT_MODEL)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.cost_tracker = get_cost_tracker()
        logger.info(f"✅ LLM client initialized (Qwen: {self.model}) with cost tracking")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = None,  # Ignored - uses Qwen model
        max_tokens: int = 1024,
        temperature: float = 0.0,
        purpose: str = "generation"
    ) -> str:
        """
        Generate text with Qwen and track costs

        Args:
            prompt: User prompt
            system: System prompt (optional)
            model: Ignored - uses Qwen model from config
            max_tokens: Maximum output tokens
            temperature: Sampling temperature (0-1)
            purpose: Description of purpose (for logging)

        Returns:
            Generated text
        """
        # Always use Qwen model
        actual_model = self.model
        logger.info(f"🤖 Calling Qwen ({actual_model}): {purpose}")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=actual_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Extract tokens from usage (if available)
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            # Log cost (will be $0 for local models)
            self.cost_tracker.log_call(
                model=actual_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                purpose=purpose
            )

            # Extract text
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"❌ Error calling Qwen: {e}")
            raise


# Convenience function
def get_claude_client() -> ClaudeClient:
    """Get LLM client with cost tracking (uses Qwen via Ollama)"""
    return ClaudeClient()


if __name__ == "__main__":
    # Test cost tracker
    tracker = get_cost_tracker()

    # Simulate some API calls (using Qwen model)
    tracker.log_call("qwen2.5:3b-instruct", input_tokens=500, output_tokens=200, purpose="test")
    tracker.log_call("qwen2.5:3b-instruct", input_tokens=1000, output_tokens=500, purpose="test")

    # Print summary
    tracker.print_summary()
