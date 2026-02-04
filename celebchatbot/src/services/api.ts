/**
 * API Service for Celebrity Chatbot
 * Connects to the Python FastAPI backend
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ChatRequest {
  celebrity_name: string;
  question: string;
  force_ingest?: boolean;
}

export interface ChatResponse {
  answer: string | null;
  decision: string | null;
  decision_reasoning: string | null;
  matches_count: number;
  error: string | null;
}

/**
 * Send a chat message to the backend
 *
 * Flow: User clicks celebrity (e.g., "Virat Kohli") → Types question →
 *       This function sends: { celebrity_name: "Virat Kohli", question: "..." } →
 *       Backend runs: python main.py --celebrity "Virat Kohli" --question "..." →
 *       Returns AI-generated answer
 */
export async function sendChatMessage(
  celebrityName: string,
  question: string,
  forceIngest: boolean = false
): Promise<ChatResponse> {
  try {
    console.log(`📤 Sending message to API:`, {
      celebrity_name: celebrityName,
      question: question
    });

    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        celebrity_name: celebrityName,
        question: question,
        force_ingest: forceIngest
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(
        errorData?.detail || `API error: ${response.status} ${response.statusText}`
      );
    }

    const data: ChatResponse = await response.json();

    console.log(`📥 Received response from API:`, data);

    return data;
  } catch (error) {
    console.error('❌ API call failed:', error);
    throw error;
  }
}

/**
 * Progress event types from streaming endpoint
 */
export interface ProgressEvent {
  type: 'start' | 'progress' | 'complete' | 'error';
  stage?: string;
  message: string;
  progress?: number;
  total?: number;
  celebrity?: string;
  answer?: string | null;
  decision?: string | null;
  decision_reasoning?: string | null;
  matches_count?: number;
  error?: string | null;
}

/**
 * Send a chat message with real-time progress updates
 *
 * Uses Server-Sent Events to stream progress:
 * - "🔍 Searching for celebrity videos..."
 * - "📹 Downloading video 3/10..."
 * - "✨ Extracting questions..."
 * - "✅ Done! Found 150 questions"
 */
export async function sendChatMessageWithProgress(
  celebrityName: string,
  question: string,
  onProgress: (event: ProgressEvent) => void,
  forceIngest: boolean = false
): Promise<ChatResponse> {
  return new Promise((resolve, reject) => {
    console.log(`📤 Starting streaming request for:`, { celebrity_name: celebrityName, question });

    const eventSource = new EventSource(
      `${API_URL}/api/chat/stream?` +
      new URLSearchParams({
        celebrity_name: celebrityName,
        question: question,
        force_ingest: forceIngest.toString()
      })
    );

    // Note: EventSource doesn't support POST, so we'll use fetch with ReadableStream instead
    fetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify({
        celebrity_name: celebrityName,
        question: question,
        force_ingest: forceIngest
      })
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete events
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const eventData: ProgressEvent = JSON.parse(line.slice(6));

                console.log('📥 Progress event:', eventData);
                onProgress(eventData);

                // If complete, resolve the promise
                if (eventData.type === 'complete') {
                  resolve({
                    answer: eventData.answer || null,
                    decision: eventData.decision || null,
                    decision_reasoning: eventData.decision_reasoning || null,
                    matches_count: eventData.matches_count || 0,
                    error: eventData.error || null
                  });
                } else if (eventData.type === 'error') {
                  reject(new Error(eventData.message));
                }
              } catch (e) {
                console.error('Error parsing SSE event:', e);
              }
            }
          }
        }
      })
      .catch((error) => {
        console.error('❌ Streaming request failed:', error);
        reject(error);
      });
  });
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<{ status: string; message: string }> {
  try {
    const response = await fetch(`${API_URL}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
}

