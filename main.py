"""
Celebrity Question Indexing & Retrieval System
Main entry point with CLI interface
"""

# Fix for segmentation fault on Mac with Python 3.13 - MUST be before any imports
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import argparse
import sys
from dotenv import load_dotenv
from agent.graph import CelebrityQuestionGraph
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_api_key():
    """Check if Claude API key is set"""
    api_key = os.getenv("CLAUDE_KEY")
    if not api_key:
        print("ERROR: CLAUDE_KEY not found in environment variables")
        print("\nPlease set your API key:")
        print("  export CLAUDE_KEY='your-api-key-here'")
        print("\nOr create a .env file with:")
        print("  CLAUDE_KEY=your-api-key-here")
        sys.exit(1)


def print_banner():
    """Print welcome banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   Celebrity Question Indexing & Retrieval System            ║
║   Agentic RAG with LangGraph                                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_query(celebrity: str, question: str, force_ingest: bool = False):
    """
    Run a query through the agentic system

    Args:
        celebrity: Celebrity name
        question: User question
        force_ingest: Force re-ingestion
    """
    print(f"\nCelebrity: {celebrity}")
    print(f"Question: {question}")
    print(f"Force Ingest: {force_ingest}")
    print("\n" + "="*60 + "\n")

    # Initialize graph
    logger.info("Initializing Celebrity Question Graph...")
    graph = CelebrityQuestionGraph()

    # Run workflow
    result = graph.run(
        celebrity_name=celebrity,
        user_question=question,
        force_ingest=force_ingest
    )

    # Display results
    print("\n" + "="*60)
    print("WORKFLOW COMPLETE")
    print("="*60 + "\n")

    print(f"Decision Made: {result['decision']}")
    print(f"Reasoning: {result['decision_reasoning']}")
    print(f"Matches Found: {result['matches_count']}")

    if result['error']:
        print(f"\n⚠️  Error: {result['error']}")

    print("\n" + "-"*60)
    print("ANSWER")
    print("-"*60 + "\n")
    print(result['answer'])
    print("\n")


def interactive_mode():
    """Run in interactive mode"""
    print_banner()
    print("Interactive Mode - Enter 'quit' to exit\n")

    graph = CelebrityQuestionGraph()

    while True:
        try:
            # Get celebrity name
            celebrity = input("\nEnter celebrity name (or 'quit'): ").strip()
            if celebrity.lower() == 'quit':
                break

            if not celebrity:
                print("Please enter a celebrity name")
                continue

            # Get question
            question = input("Enter your question: ").strip()
            if not question:
                print("Please enter a question")
                continue

            # Ask about force ingest
            force = input("Force re-ingestion? (y/N): ").strip().lower()
            force_ingest = force == 'y'

            # Run query
            print("\n" + "="*60)
            result = graph.run(
                celebrity_name=celebrity,
                user_question=question,
                force_ingest=force_ingest
            )

            # Display results
            print("\n" + "="*60)
            print("RESULT")
            print("="*60 + "\n")

            print(f"Decision: {result['decision']}")
            print(f"Matches: {result['matches_count']}\n")
            print(result['answer'])
            print("\n")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            logger.exception("Error in interactive mode")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Celebrity Question Indexing & Retrieval System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python main.py

  # Single query
  python main.py --celebrity "Keanu Reeves" --question "What inspired you to become an actor?"

  # Force re-ingestion
  python main.py --celebrity "Keanu Reeves" --question "What's your favorite role?" --force-ingest

  # Batch mode (from file)
  python main.py --batch queries.txt
        """
    )

    parser.add_argument(
        '-c', '--celebrity',
        type=str,
        help='Celebrity name'
    )

    parser.add_argument(
        '-q', '--question',
        type=str,
        help='Question to ask'
    )

    parser.add_argument(
        '-f', '--force-ingest',
        action='store_true',
        help='Force re-ingestion even if data exists'
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )

    parser.add_argument(
        '-b', '--batch',
        type=str,
        help='Batch mode: process queries from file'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(args.log_level)

    # Check API key
    check_api_key()

    # Interactive mode
    if args.interactive or (not args.celebrity and not args.batch):
        interactive_mode()
        return

    # Batch mode
    if args.batch:
        print_banner()
        print(f"Batch mode: Processing queries from {args.batch}\n")

        if not os.path.exists(args.batch):
            print(f"Error: File not found: {args.batch}")
            sys.exit(1)

        graph = CelebrityQuestionGraph()

        with open(args.batch, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                try:
                    # Expected format: celebrity|question
                    celebrity, question = line.split('|', 1)
                    celebrity = celebrity.strip()
                    question = question.strip()

                    print(f"\n[Query {line_num}] {celebrity}: {question}")
                    result = graph.run(celebrity, question)
                    print(f"Result: {result['matches_count']} matches")

                except ValueError:
                    print(f"Error on line {line_num}: Invalid format (expected: celebrity|question)")
                except Exception as e:
                    print(f"Error on line {line_num}: {e}")

        return

    # Single query mode
    if not args.celebrity or not args.question:
        parser.print_help()
        sys.exit(1)

    print_banner()
    run_query(args.celebrity, args.question, args.force_ingest)


if __name__ == "__main__":
    main()
