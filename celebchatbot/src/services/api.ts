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

