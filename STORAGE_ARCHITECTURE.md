# Storage Architecture Explanation

## What is stored where?

### 1. **Vector Database (FAISS)** 📊
**Location**: `data/faiss_indexes/{celebrity_name}.faiss`

**What it stores**:
- **ONLY embeddings** (384-dimensional vectors)
- Each question is converted to a mathematical vector representation
- Vectors are normalized for cosine similarity search
- Fast similarity search using inner product

**Example**:
```
Vector ID 0: [0.123, -0.456, 0.789, ... 384 numbers]
Vector ID 1: [0.234, -0.567, 0.891, ... 384 numbers]
Vector ID 2: [0.345, -0.678, 0.912, ... 384 numbers]
```

**What it DOES NOT store**:
- ❌ Question text
- ❌ Source URLs
- ❌ Timestamps
- ❌ Any metadata

**Why use FAISS?**
- Lightning-fast similarity search
- Can search millions of vectors in milliseconds
- Efficient memory usage for large datasets

---

### 2. **Metadata Store (JSON)** 📝
**Location**: `data/metadata/{celebrity_name}_metadata.json`

**What it stores**:
- **ALL the actual question data**
- Maps FAISS ID → Full metadata

**Example**:
```json
{
  "0": {
    "celebrity_name": "Virat Kohli",
    "question_text": "What inspired you to become a cricketer?",
    "source_type": "youtube",
    "source_url": "https://www.youtube.com/watch?v=abc123&t=150",
    "source_title": "Virat Kohli Interview 2024",
    "timestamp": 150.5,
    "date": "2024-01-15",
    "indexed_at": "2026-01-25T20:14:26.826779"
  },
  "1": {
    "celebrity_name": "Virat Kohli",
    "question_text": "How do you handle pressure?",
    "source_type": "podcast",
    "source_url": "https://podcast.com/episode-5",
    "source_title": "Sports Talk Podcast - Episode 5",
    "timestamp": null,
    "date": "2024-02-10",
    "indexed_at": "2026-01-25T20:14:26.826785"
  }
}
```

---

## How they work together

### **Indexing (Storing Questions)**:
```
Question: "What inspired you?"
    ↓
1. Generate embedding using sentence-transformer
   → [0.123, -0.456, 0.789, ... 384 numbers]
    ↓
2. Add vector to FAISS index
   → Assigned FAISS ID: 42
    ↓
3. Store metadata in JSON
   → metadata[42] = {text, source, url, timestamp...}
```

### **Retrieval (Searching)**:
```
User Query: "What motivated you to play cricket?"
    ↓
1. Generate embedding for query
   → [0.234, -0.567, 0.891, ... 384 numbers]
    ↓
2. Search FAISS for similar vectors
   → Top matches: IDs [42, 108, 256] with similarity scores
    ↓
3. Look up metadata for each ID
   → metadata[42] → "What inspired you?" from YouTube
   → metadata[108] → "Why did you choose cricket?" from Podcast
   → metadata[256] → "What was your motivation?" from Article
    ↓
4. Return results with all source information
```

---

## Why this two-tier architecture?

### **Separation of Concerns**:
- **FAISS**: Fast mathematical operations on vectors
- **JSON**: Rich metadata storage with full context

### **Advantages**:
1. ✅ **Speed**: FAISS searches millions of vectors in milliseconds
2. ✅ **Flexibility**: Easy to add/modify metadata without rebuilding vectors
3. ✅ **Scalability**: Can handle large amounts of data efficiently
4. ✅ **Debugging**: Can inspect metadata JSON files directly
5. ✅ **Recovery**: If one fails, the other is still intact

### **Example Workflow**:
```
User: "What inspired Virat Kohli?"
  → FAISS finds similar questions (0.001ms per vector)
  → Metadata provides full context (question text, sources, timestamps)
  → System returns: "This question was asked in 3 different interviews:
      1. YouTube video at 2:30 timestamp
      2. Podcast episode on Feb 10
      3. GQ Magazine article"
```

---

## File Sizes

### FAISS Index:
- ~1.5 KB per question (384 floats × 4 bytes)
- 1,000 questions ≈ 1.5 MB
- 100,000 questions ≈ 150 MB

### Metadata JSON:
- ~500 bytes per question (text + metadata)
- 1,000 questions ≈ 500 KB
- 100,000 questions ≈ 50 MB

---

## Current Issue: Deduplication

### **Current Behavior** (WRONG):
```
YouTube: "What inspired you to play cricket?"
Podcast: "What made you want to play cricket?"
Article: "Why did you choose cricket?"

→ System sees these as similar (85%+ similarity)
→ Deduplicates to 1 entry
→ Loses individual source information
```

### **Desired Behavior** (CORRECT):
```
YouTube: "What inspired you to play cricket?"
Podcast: "What made you want to play cricket?"
Article: "Why did you choose cricket?"

→ Store ALL 3 separately
→ When user asks similar question
→ Show ALL 3 sources with their different phrasings
```

This allows users to see:
- How the same topic was discussed in different contexts
- Different interviewers' perspectives
- Evolution of answers over time
- Multiple sources for verification

---

## Next Step

I'll now disable the deduplication so ALL questions are stored with their individual sources, even if they're similar.
