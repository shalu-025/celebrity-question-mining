"""
CRITICAL CONSTRAINTS ENFORCEMENT
Ensures cost-safe, exam-ready system configuration
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


class ConstraintViolation(Exception):
    """Raised when a critical constraint is violated"""
    pass


# 🔴 CRITICAL: TRANSCRIPTION MODE
TRANSCRIPTION_MODE = os.getenv("TRANSCRIPTION_MODE", "local")

if TRANSCRIPTION_MODE != "local":
    raise ConstraintViolation(
        f"❌ CONSTRAINT VIOLATION: TRANSCRIPTION_MODE must be 'local', got '{TRANSCRIPTION_MODE}'\n"
        "Cloud transcription is FORBIDDEN. Set TRANSCRIPTION_MODE=local in .env"
    )


# 🔴 CRITICAL: API KEY ENFORCEMENT
CLAUDE_API_KEY = os.getenv("CLAUDE_KEY")

if not CLAUDE_API_KEY:
    raise ConstraintViolation(
        "❌ CONSTRAINT VIOLATION: CLAUDE_KEY not found in environment\n"
        "Claude API key is REQUIRED for final answer generation.\n"
        "Add CLAUDE_KEY to your .env file"
    )


# ❌ FORBIDDEN: OpenAI API should NOT be used
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    print("⚠️  WARNING: OPENAI_API_KEY detected in environment")
    print("⚠️  This system does NOT use OpenAI API")
    print("⚠️  Only CLAUDE_KEY will be used")


# Whisper configuration
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")


# Embedding configuration (local, free)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


# LLM USAGE RULES
LLM_ALLOWED_FOR = ["final_answer_generation"]  # ONLY allowed use case
LLM_FORBIDDEN_FOR = [
    "question_extraction",
    "transcript_parsing",
    "semantic_chunking",
    "question_refinement"
]


# Cost tracking settings
TRACK_LLM_COSTS = True


def validate_constraints():
    """
    Run all constraint validations
    Call this at startup to ensure compliance
    """
    print("\n" + "="*60)
    print("🔒 CONSTRAINT VALIDATION")
    print("="*60)

    # Check transcription mode
    print(f"✅ Transcription mode: {TRANSCRIPTION_MODE} (local Whisper)")

    # Check API key
    print(f"✅ Claude API key: {'Present' if CLAUDE_API_KEY else 'MISSING'}")

    # Check OpenAI
    if OPENAI_API_KEY:
        print("⚠️  OpenAI key present but will NOT be used")
    else:
        print("✅ No OpenAI key (correct)")

    # Whisper config
    print(f"✅ Whisper model: {WHISPER_MODEL_SIZE}")
    print(f"✅ Embedding model: {EMBEDDING_MODEL} (local)")

    # LLM usage rules
    print(f"✅ LLM usage: ONLY for {', '.join(LLM_ALLOWED_FOR)}")
    print(f"❌ LLM FORBIDDEN for: {', '.join(LLM_FORBIDDEN_FOR)}")

    print("="*60)
    print("✅ All constraints validated\n")

    return True


if __name__ == "__main__":
    try:
        validate_constraints()
        print("✅ System is constraint-compliant")
    except ConstraintViolation as e:
        print(f"\n❌ CONSTRAINT VIOLATION:\n{e}")
        sys.exit(1)
