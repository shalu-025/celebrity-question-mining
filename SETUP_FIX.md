# Setup Fix for Mac Segfault Issue

## Problem
The original `openai-whisper` library causes segmentation faults on Mac with Python 3.13. This has been fixed by switching to `faster-whisper`, which is:
- ✅ Still completely **local** (no cloud API)
- ✅ Still **free** ($0 cost)
- ✅ More **stable** on Mac
- ✅ Actually **faster** than openai-whisper

## Solution

### Step 1: Install Updated Dependencies

```bash
# Activate your virtual environment first
conda activate celeb  # or: source celeb/bin/activate

# Install faster-whisper (replaces openai-whisper)
pip install faster-whisper>=1.0.0

# Install Anthropic SDK for Claude API
pip install anthropic>=0.39.0

# Or install all dependencies from updated requirements.txt
pip install -r requirements.txt
```

### Step 2: Verify Installation

```bash
# Test that faster-whisper works
python -c "from faster_whisper import WhisperModel; print('✅ faster-whisper installed')"

# Test that anthropic works
python -c "from anthropic import Anthropic; print('✅ anthropic installed')"
```

### Step 3: Verify Constraints

```bash
# Run constraint validation
python -c "from config.constraints import validate_constraints; validate_constraints()"
```

Expected output:
```
============================================================
🔒 CONSTRAINT VALIDATION
============================================================
✅ Transcription mode: local (local Whisper)
✅ Claude API key: Present
✅ No OpenAI key (correct)
✅ Whisper model: small
✅ Embedding model: all-MiniLM-L6-v2 (local)
✅ LLM usage: ONLY for final_answer_generation
❌ LLM FORBIDDEN for: question_extraction, transcript_parsing, semantic_chunking, question_refinement
============================================================
✅ All constraints validated
```

### Step 4: Test the Pipeline

```bash
# Extract questions from a celebrity (will download videos and transcribe locally)
python extract_questions.py "Keanu Reeves" --max-videos 1
```

This should now work without segfaults!

## What Changed?

### Dependencies
- ❌ Removed: `openai-whisper` (causes segfaults on Mac)
- ✅ Added: `faster-whisper` (stable, local, faster)
- ❌ Removed: `openai` (for OpenAI API)
- ✅ Added: `anthropic` (for Claude API)

### Code Changes
- [transcription/whisper_transcriber.py](transcription/whisper_transcriber.py) - Now uses `faster-whisper` library
- All other changes maintain **100% compliance** with constraints

## Benefits of Faster-Whisper

1. **No More Segfaults**: Works reliably on Mac with Python 3.13+
2. **Faster**: Uses CTranslate2 for optimized inference
3. **Lower Memory**: More efficient memory usage
4. **Still Local**: Runs completely offline, no cloud API
5. **Same API**: Almost identical interface to openai-whisper

## Still Compliant with All Constraints

✅ **Speech-to-Text**: Uses local Faster-Whisper (NO cloud API)
✅ **Extraction**: Rule-based heuristics only (NO LLM)
✅ **LLM Usage**: Claude API only for final answer (optional)
✅ **Cost**: $0 for main workflow
✅ **Cost Tracking**: Automatic logging for any LLM usage

## Troubleshooting

### If you still get errors:

1. **Make sure ffmpeg is installed**:
   ```bash
   # On Mac with Homebrew
   brew install ffmpeg

   # Verify installation
   ffmpeg -version
   ```

2. **Try a smaller Whisper model**:
   ```python
   # In extract_questions.py or your code
   transcriber = get_transcriber("tiny")  # Faster, lower memory
   ```

3. **Check your .env file**:
   ```bash
   cat .env | grep TRANSCRIPTION_MODE
   # Should show: TRANSCRIPTION_MODE=local

   cat .env | grep CLAUDE_KEY
   # Should show your Claude API key
   ```

## Additional Notes

- First run will download Whisper model files (~150MB for 'base' model)
- Models are cached in `~/.cache/huggingface/`
- Faster-Whisper is actually used in production by many companies for its stability

## Contact

If you still experience issues after following these steps, the problem might be:
- Missing ffmpeg installation
- Corrupted audio files
- Insufficient disk space

Check the error logs and verify your setup step by step.
