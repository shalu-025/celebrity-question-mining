# Complete Setup Guide - Celebrity Chatbot with Qwen

## ✅ What's Working Now

1. **Qwen Model Installed** (`qwen2.5:3b-instruct`) - Local, FREE AI!
2. **Auto-Ingestion** - Automatically downloads celebrity data when needed
3. **UI → Backend Integration** - Click celebrity → Get AI answer
4. **Search Functionality** - Search for any celebrity, system auto-ingests if needed

---

## 🚀 How to Run Everything

### Terminal 1: Start Backend API

```bash
cd /Users/bhargavigundabathina/Documents/celeb/celebrity-question-mining
python3 api_server.py
```

**Expected output:**
```
🚀 Starting Celebrity Question API Server...
📡 API will be available at: http://localhost:8000
✅ LLM client initialized (Qwen: qwen2.5:3b-instruct)
```

### Terminal 2: Start Frontend UI

Open a **NEW** terminal:

```bash
cd /Users/bhargavigundabathina/Documents/celeb/celebrity-question-mining/celebchatbot
npm run dev
```

**Expected output:**
```
VITE ready in xxx ms
➜  Local:   http://localhost:8080/
```

### Terminal 3: Verify Ollama is Running

```bash
# Check Ollama status
ollama list

# Should show:
# qwen2.5:3b-instruct    357c53fb659c    1.9 GB    ...
```

---

## 📊 How the System Works

### Flow 1: User Clicks Existing Celebrity (e.g., "Virat Kohli")

```
1. User clicks "Virat Kohli" on UI
   ↓
2. Frontend sends to API:
   POST /api/chat
   { celebrity_name: "Virat Kohli", question: "what is favorite color?" }
   ↓
3. Backend runs (equivalent to):
   python main.py --celebrity "Virat Kohli" --question "what is favorite color?"
   ↓
4. Decision Agent checks registry:
   - If Virat Kohli data EXISTS → RETRIEVE
   - If NO data exists → INGEST (auto-download from YouTube/podcasts/articles)
   ↓
5. Qwen AI generates answer from retrieved data
   ↓
6. Frontend displays answer in chat
```

### Flow 2: User Searches for New Celebrity

```
1. User types "Elon Musk" in search bar
   ↓
2. System checks: Does "Elon Musk" data exist?
   - NO → Decision: INGEST
   ↓
3. Ingestion starts automatically:
   - YouTube videos about Elon Musk
   - Podcast episodes
   - News articles
   - Extracts questions + answers
   - Stores in vector database
   ↓
4. After ingestion → RETRIEVE answers
   ↓
5. User gets response!
```

---

## 🔧 Configuration

### Environment Variables (.env)

Your `.env` file should have:

```bash
# For Qwen (local model) - NOT REQUIRED, it's local!
# QWEN_API_KEY=ollama
# QWEN_BASE_URL=http://localhost:11434/v1
# QWEN_MODEL=qwen2.5:3b-instruct

# Only needed if you want to use Claude instead:
# CLAUDE_KEY=sk-ant-your-key-here
```

### Key Files

```
celebrity-question-mining/
├── api_server.py                    # FastAPI server (YOUR ENTRY POINT)
├── main.py                          # CLI interface (for testing)
├── .env                             # Configuration
├── agent/
│   ├── graph.py                     # LangGraph workflow
│   └── decision_node.py             # Auto-ingest decision logic
├── utils/
│   └── llm_cost_tracker.py          # Qwen configuration
├── registry/
│   └── celebrity_index.json         # Tracks indexed celebrities
├── vector_db/
│   └── indexes/                     # FAISS vector databases
└── celebchatbot/                    # React frontend
    └── src/
        ├── services/api.ts          # API calls
        └── pages/CelebrityDetail.tsx # Chat UI
```

---

## 🧪 Testing

### Test 1: CLI (Direct Python)

```bash
cd /Users/bhargavigundabathina/Documents/celeb/celebrity-question-mining

python main.py \
  --celebrity "Keanu Reeves" \
  --question "What inspired you to become an actor?"
```

### Test 2: API Endpoint

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "celebrity_name": "Virat Kohli",
    "question": "What is your favorite color?"
  }'
```

### Test 3: Full UI Flow

1. Start both servers (Terminal 1 + Terminal 2)
2. Open http://localhost:8080
3. Click "Virat Kohli"
4. Type: "What is your favorite color?"
5. Press Enter
6. See AI response! 🎉

---

## 🐛 Troubleshooting

### Error: "model 'qwen2.5:3b-instruct' not found"

**Solution:**
```bash
ollama pull qwen2.5:3b-instruct
```

### Error: "No index found for [Celebrity]"

**Cause:** Celebrity data hasn't been ingested yet.

**Solution:**
1. System will auto-ingest on first request (takes 2-5 minutes)
2. Or manually run:
   ```bash
   python main.py --celebrity "Celebrity Name" --question "test" --force-ingest
   ```

### Error: "Connection refused" from UI

**Solution:** Make sure backend is running on port 8000:
```bash
lsof -i:8000
# Should show python3 running api_server.py
```

### Ollama Not Running

**Solution:**
```bash
# Start Ollama service
ollama serve &

# Check it's running
ps aux | grep ollama
```

---

## 📁 Data Storage

### Registry
- **Location:** `registry/celebrity_index.json`
- **Contains:** Metadata about indexed celebrities
- **Format:**
  ```json
  {
    "celebrities": {
      "Virat Kohli": {
        "last_indexed": "2026-02-04T00:00:00",
        "sources_count": 150,
        "questions_count": 200
      }
    }
  }
  ```

### Vector Database
- **Location:** `vector_db/indexes/`
- **Format:** FAISS index files (`.faiss` + `.pkl`)
- **Contents:** Embeddings of questions + metadata

---

## 🎯 What Happens When You Click a Celebrity

```
UI Click: "Virat Kohli"
    ↓
CelebrityDetail.tsx loads with celebrity.name = "Virat Kohli"
    ↓
User types question: "What is your favorite color?"
    ↓
handleSend() calls:
sendChatMessage("Virat Kohli", "What is your favorite color?")
    ↓
API POST to http://localhost:8000/api/chat
Body: {
  celebrity_name: "Virat Kohli",
  question: "What is your favorite color?"
}
    ↓
api_server.py receives request
    ↓
graph.run("Virat Kohli", "What is your favorite color?")
    ↓
EQUIVALENT TO CLI:
python main.py \
  --celebrity "Virat Kohli" \
  --question "What is your favorite color?"
    ↓
Decision Agent checks registry
    ↓
IF celebrity NOT indexed:
  → INGEST (download YouTube/podcasts/articles)
  → Extract questions
  → Store in vector database
  → Continue to RETRIEVE
    ↓
IF celebrity ALREADY indexed:
  → RETRIEVE from vector database
    ↓
Find similar questions from interviews
    ↓
Qwen AI formats answer
    ↓
Return to frontend
    ↓
Display in chat! ✅
```

---

## 🌟 Features

### Auto-Ingestion ✅
- No manual data setup needed
- System automatically downloads data when needed
- Works for ANY celebrity you click or search

### Smart Caching ✅
- Once celebrity data is ingested, it's stored
- Future questions are instant (no re-download)
- Updates automatically if data is stale

### Free & Local ✅
- Uses Qwen (local model via Ollama)
- No API costs
- All data stored locally
- Privacy-friendly

### Scalable ✅
- Add new celebrities instantly (just search!)
- System handles data freshness
- Automatic source discovery

---

## 🚀 Ready to Use!

1. **Start Backend:** `cd celebrity-question-mining && python3 api_server.py`
2. **Start Frontend:** `cd celebrity-question-mining/celebchatbot && npm run dev`
3. **Open Browser:** http://localhost:8080
4. **Click Celebrity & Chat!** 🎉

---

## 💡 Pro Tips

- **First Request Takes Time:** If celebrity not indexed, wait 2-5 mins for ingestion
- **Subsequent Requests Are Fast:** Once indexed, answers are instant
- **Check Logs:** Watch Terminal 1 to see ingestion progress
- **Add New Celebrities:** Just search/click them - system handles the rest!
