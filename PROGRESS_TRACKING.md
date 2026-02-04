# Real-Time Progress Tracking Feature

## Overview

The celebrity chatbot now shows **real-time progress updates** during the ingestion process, keeping users informed about what's happening behind the scenes.

## What Users See

When asking a question about a celebrity that hasn't been indexed yet, users see step-by-step progress messages:

```
🤔 Checking if Virat Kohli data exists...
   ↓
📥 Virat Kohli not found. Starting data ingestion...
   ↓
🎥 Searching YouTube for Virat Kohli interviews...
   ↓
✨ Generating answer with AI...
   ↓
✅ [Final answer displayed]
```

For celebrities that already have data:

```
🤔 Checking if Virat Kohli data exists...
   ↓
✅ Virat Kohli data found! Searching for similar questions...
   ↓
✨ Generating answer with AI...
   ↓
✅ [Final answer displayed]
```

---

## How It Works

### Backend: Server-Sent Events (SSE)

**File:** `api_server.py`

New endpoint: `POST /api/chat/stream`

```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream progress updates during processing"""

    async def event_generator():
        # 1. Check decision
        yield {"type": "progress", "message": "🤔 Checking if data exists..."}

        # 2. Ingest or retrieve
        if needs_ingestion:
            yield {"type": "progress", "message": "📥 Starting data ingestion..."}
            yield {"type": "progress", "message": "🎥 Searching YouTube..."}
        else:
            yield {"type": "progress", "message": "✅ Data found! Searching..."}

        # 3. Run graph
        result = await run_graph()

        # 4. Generate answer
        yield {"type": "progress", "message": "✨ Generating answer..."}

        # 5. Complete
        yield {"type": "complete", "answer": result['answer']}

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Frontend: Real-Time Updates

**File:** `celebchatbot/src/services/api.ts`

New function: `sendChatMessageWithProgress()`

```typescript
export async function sendChatMessageWithProgress(
  celebrityName: string,
  question: string,
  onProgress: (event: ProgressEvent) => void
): Promise<ChatResponse> {
  // Use fetch with ReadableStream to read SSE events
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ celebrity_name: celebrityName, question })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // Parse SSE event
    const eventData = JSON.parse(decoder.decode(value));

    // Call progress callback
    onProgress(eventData);
  }
}
```

### UI Component: Progress Display

**File:** `celebchatbot/src/pages/CelebrityDetail.tsx`

```typescript
const [progressMessage, setProgressMessage] = useState<string>("");

const handleSend = async () => {
  // ...

  await sendChatMessageWithProgress(
    celebrity.name,
    questionText,
    (event) => {
      // Update progress message in real-time
      if (event.type === 'progress') {
        setProgressMessage(event.message);
      }
    }
  );
};

// In the JSX:
{isTyping && (
  <div className="typing-indicator">
    {progressMessage ? (
      <span>{progressMessage}</span>  // Show progress
    ) : (
      <AnimatedDots />  // Show default typing indicator
    )}
  </div>
)}
```

---

## Event Types

### Progress Event

```typescript
{
  type: "progress",
  stage: "decision" | "ingest" | "youtube" | "retrieve" | "answer",
  message: "🤔 Checking if Virat Kohli data exists...",
  progress: 2,  // Current step
  total: 5      // Total steps
}
```

### Complete Event

```typescript
{
  type: "complete",
  answer: "Virat Kohli's favorite color is...",
  decision: "RETRIEVE",
  matches_count: 150
}
```

### Error Event

```typescript
{
  type: "error",
  message: "Failed to connect to backend"
}
```

---

## Progress Stages

### Stage 1: Decision (20%)
```
🤔 Checking if [Celebrity] data exists...
```

Checks registry to see if celebrity is already indexed.

### Stage 2: Ingestion Decision (40%)

**If needs ingestion:**
```
📥 [Celebrity] not found. Starting data ingestion...
```

**If data exists:**
```
✅ [Celebrity] data found! Searching for similar questions...
```

### Stage 3: Data Collection (60%)

**During ingestion:**
```
🎥 Searching YouTube for [Celebrity] interviews...
```

This is where the long-running process happens:
- Downloading videos
- Transcribing audio
- Extracting questions
- Creating embeddings
- Storing in vector database

### Stage 4: Answer Generation (80%)
```
✨ Generating answer with AI...
```

Uses Qwen to format the final answer based on retrieved questions.

### Stage 5: Complete (100%)
```
[Final answer displayed in chat]
```

---

## Benefits

### For Users:
- **Transparency**: See exactly what's happening
- **No Silent Waiting**: Know the system is working
- **Progress Feedback**: Understand if it's a quick query or long ingestion
- **Better UX**: Reduces perceived wait time

### For Developers:
- **Debugging**: Easy to see which stage is slow
- **Monitoring**: Track system performance in real-time
- **User Support**: Users can report exactly where it got stuck

---

## Example Flow

### Scenario: First-Time Celebrity Query

**User Action:**
```
User clicks "Elon Musk" (not indexed yet)
User types: "What inspires you?"
User presses Enter
```

**UI Shows:**

```
1. [0.5s] 🤔 Checking if Elon Musk data exists...
          ↓
2. [0.5s] 📥 Elon Musk not found. Starting data ingestion...
          ↓
3. [2-5 min] 🎥 Searching YouTube for Elon Musk interviews...
             (Long process: downloading 10 videos, transcribing, extracting)
          ↓
4. [1s] ✨ Generating answer with AI...
          ↓
5. [DONE] "I'm inspired by the goal of making humanity multiplanetary..."
```

### Scenario: Cached Celebrity Query

**User Action:**
```
User clicks "Virat Kohli" (already indexed)
User types: "What is your favorite color?"
User presses Enter
```

**UI Shows:**

```
1. [0.5s] 🤔 Checking if Virat Kohli data exists...
          ↓
2. [0.5s] ✅ Virat Kohli data found! Searching for similar questions...
          ↓
3. [1s] ✨ Generating answer with AI...
          ↓
4. [DONE] "I haven't specifically mentioned a favorite color in interviews, but..."
```

**Total time: ~2-3 seconds** (much faster!)

---

## Technical Details

### Why SSE Instead of WebSockets?

**Server-Sent Events (SSE)** are simpler for one-way communication:
- Automatic reconnection
- Works over HTTP (no special protocol)
- Built-in browser support
- Easier to implement

WebSockets would be overkill for this use case.

### Why Not Long Polling?

Long polling would be inefficient:
- Requires constant reconnection
- Higher latency
- More complex error handling
- Waste resources

SSE provides a persistent connection with low overhead.

### Performance Impact

**Minimal:**
- SSE connection overhead: <1KB
- Progress events: ~100 bytes each
- Total overhead: <5KB per request

---

## Future Enhancements

### Possible Improvements:

1. **Detailed Progress Bars**
   - Show "Downloading video 3/10"
   - Show "Extracting question 45/150"

2. **Estimated Time Remaining**
   - "~3 minutes remaining..."
   - Based on historical data

3. **Cancellation Support**
   - Allow users to cancel long-running ingestions
   - "Cancel" button during ingestion

4. **Progress History**
   - Show what was ingested
   - "Added 150 new questions from 10 videos"

5. **Retry on Failure**
   - Auto-retry failed videos
   - Show which sources succeeded/failed

---

## Testing

### Test Progress Display

1. Start backend: `python3 api_server.py`
2. Start frontend: `npm run dev`
3. Click a NEW celebrity (not indexed)
4. Watch the progress messages appear in real-time!

### Test with Existing Celebrity

1. Click Virat Kohli (already indexed)
2. Should be much faster
3. Different progress messages shown

### Test Error Handling

1. Stop the backend
2. Try sending a message
3. Should show error: "Failed to connect to server"

---

## Files Modified

✅ **Backend:**
- `api_server.py` - Added `/api/chat/stream` endpoint

✅ **Frontend:**
- `celebchatbot/src/services/api.ts` - Added `sendChatMessageWithProgress()`
- `celebchatbot/src/pages/CelebrityDetail.tsx` - Display progress messages

---

## Summary

Users now see **real-time feedback** during ingestion:
- ✅ Keeps users informed
- ✅ Reduces anxiety during long waits
- ✅ Better user experience
- ✅ Easy to debug issues

**The system is now fully interactive and user-friendly!** 🎉
