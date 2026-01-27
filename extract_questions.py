"""
Question Extraction Pipeline
Cost-safe, exam-ready system

Workflow:
1. Download YouTube video audio (yt-dlp)
2. Transcribe with local Whisper (NO cloud API)
3. Extract questions with rule-based heuristics (NO LLM)
4. Output as Markdown report
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment and validate constraints FIRST
load_dotenv()

# Validate critical constraints before any imports
from config.constraints import validate_constraints

print("\n🔒 Validating system constraints...")
validate_constraints()

# Now import other modules
from ingestion.youtube_ingest import YouTubeIngester
from processing.semantic_chunker import get_semantic_chunker
from utils.llm_cost_tracker import get_cost_tracker
from utils.logger import get_logger

logger = get_logger(__name__)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def generate_markdown_report(
    questions: list,
    celebrity_name: str,
    output_path: str
):
    """
    Generate Markdown report of extracted questions

    Args:
        questions: List of question dicts
        celebrity_name: Celebrity name
        output_path: Output file path
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# Questions Asked to {celebrity_name}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Questions Extracted:** {len(questions)}\n\n")
        f.write("---\n\n")

        # Group by source
        sources = {}
        for q in questions:
            source_title = q.get('source_title', 'Unknown Source')
            if source_title not in sources:
                sources[source_title] = []
            sources[source_title].append(q)

        # Write questions by source
        for source_title, source_questions in sources.items():
            f.write(f"## {source_title}\n\n")
            f.write(f"**Questions in this source:** {len(source_questions)}\n\n")

            for idx, q in enumerate(source_questions, 1):
                timestamp = q.get('timestamp', 0)
                source_url = q.get('source_url', '#')
                question_text = q['text']

                f.write(f"### {idx}. {question_text}\n\n")
                f.write(f"- **Timestamp:** {format_timestamp(timestamp)}\n")
                f.write(f"- **Link:** [{format_timestamp(timestamp)}]({source_url})\n")

                if q.get('date'):
                    f.write(f"- **Date:** {q['date']}\n")

                f.write("\n")

            f.write("---\n\n")

        # Footer
        f.write("\n## Extraction Method\n\n")
        f.write("- **Audio Download:** yt-dlp (local)\n")
        f.write("- **Transcription:** Whisper (local, no cloud API)\n")
        f.write("- **Question Extraction:** Rule-based heuristics (no LLM)\n")
        f.write("- **Cost:** $0 (all processing is local)\n")

    logger.info(f"✅ Markdown report saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract questions from celebrity interviews (YouTube)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract questions from Keanu Reeves interviews
  python extract_questions.py "Keanu Reeves" --max-videos 3

  # Extract with custom output path
  python extract_questions.py "Margot Robbie" --output margot_questions.md

  # Extract and deduplicate similar questions
  python extract_questions.py "Tom Hanks" --deduplicate
        """
    )

    parser.add_argument(
        'celebrity',
        type=str,
        help='Celebrity name (e.g., "Keanu Reeves")'
    )

    parser.add_argument(
        '--max-videos',
        type=int,
        default=5,
        help='Maximum number of videos to process (default: 5)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output markdown file path (default: data/questions_<celebrity>.md)'
    )

    parser.add_argument(
        '--deduplicate',
        action='store_true',
        help='Remove duplicate/similar questions using embeddings'
    )

    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=0.85,
        help='Similarity threshold for deduplication (0-1, default: 0.85)'
    )

    args = parser.parse_args()

    # Setup
    celebrity_name = args.celebrity
    max_videos = args.max_videos

    if args.output:
        output_path = args.output
    else:
        # Default output path
        safe_name = celebrity_name.lower().replace(' ', '_')
        output_path = f"data/questions_{safe_name}.md"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    print(f"\n{'='*60}")
    print(f"🎬 Celebrity Question Extraction")
    print(f"{'='*60}")
    print(f"Celebrity: {celebrity_name}")
    print(f"Max videos: {max_videos}")
    print(f"Output: {output_path}")
    print(f"Deduplication: {'Enabled' if args.deduplicate else 'Disabled'}")
    print(f"{'='*60}\n")

    # Initialize cost tracker
    cost_tracker = get_cost_tracker()

    try:
        # Step 1: Ingest from YouTube
        print("📥 Step 1: Downloading and processing YouTube videos...")
        ingester = YouTubeIngester()
        questions = ingester.ingest_celebrity(celebrity_name, max_videos=max_videos)

        if not questions:
            print(f"❌ No questions found for {celebrity_name}")
            return

        print(f"✅ Extracted {len(questions)} questions\n")

        # Step 2: Deduplicate (optional)
        if args.deduplicate:
            print("🔄 Step 2: Deduplicating similar questions...")
            chunker = get_semantic_chunker(similarity_threshold=args.similarity_threshold)
            questions = chunker.deduplicate_questions(questions)
            print(f"✅ After deduplication: {len(questions)} unique questions\n")

        # Step 3: Generate Markdown report
        print("📝 Step 3: Generating Markdown report...")
        generate_markdown_report(questions, celebrity_name, output_path)

        # Final summary
        print(f"\n{'='*60}")
        print("✅ EXTRACTION COMPLETE")
        print(f"{'='*60}")
        print(f"Questions extracted: {len(questions)}")
        print(f"Output file: {output_path}")
        print(f"{'='*60}\n")

        # Print cost summary (should be $0 since no LLM used)
        cost_tracker.print_summary()

    except Exception as e:
        logger.error(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
