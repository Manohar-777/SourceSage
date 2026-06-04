export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Analyze a GitHub repository via SSE streaming.
 *
 * The backend uses sse-starlette which sends named events:
 *   event: clone_start\n
 *   data: {"repo_url":"..."}\n\n
 *
 * @param {string} repoUrl - The GitHub repository URL
 * @param {string} apiKey - Gemini API key (sent as X-API-Key header)
 * @param {function} onEvent - Callback for each SSE event: { type, data }
 * @returns {Promise<void>}
 */
export async function analyzeRepo(repoUrl, apiKey, onEvent) {
  try {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify({
        repo_url: repoUrl,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE messages are separated by double newlines
      const messages = buffer.split('\n\n');
      // Keep the last (possibly incomplete) chunk in the buffer
      buffer = messages.pop() || '';

      for (const message of messages) {
        if (!message.trim()) continue;

        let eventType = 'message';
        let eventData = null;

        for (const line of message.split('\n')) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            eventType = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            const jsonStr = trimmed.slice(5).trim();
            if (jsonStr === '[DONE]') {
              onEvent({ type: 'done', data: null });
              return;
            }
            try {
              eventData = JSON.parse(jsonStr);
            } catch {
              console.warn('Skipping malformed SSE data:', jsonStr);
            }
          }
        }

        if (eventData !== null) {
          onEvent({ type: eventType, data: eventData });
        }
      }
    }

    // Stream ended
    onEvent({ type: 'done', data: null });
  } catch (error) {
    if (error.name === 'AbortError') {
      onEvent({ type: 'cancelled', data: null });
      return;
    }
    onEvent({
      type: 'error',
      data: {
        message: error.message || 'Failed to connect to analysis server. Is the backend running?',
      },
    });
  }
}

/**
 * Generate documentation for a repository.
 * @param {string} repoUrl
 * @param {string} apiKey
 * @returns {Promise<object>}
 */
export async function generateDocs(repoUrl, apiKey) {
  try {
    const response = await fetch(`${API_BASE}/api/generate-docs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: JSON.stringify({
        repo_url: repoUrl,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw new Error(
      error.message || 'Failed to generate documentation. Please try again.'
    );
  }
}

/**
 * Check backend health.
 * @returns {Promise<object>}
 */
export async function healthCheck() {
  try {
    const response = await fetch(`${API_BASE}/api/health`, {
      method: 'GET',
    });
    if (!response.ok) {
      throw new Error('Backend unhealthy');
    }
    return await response.json();
  } catch {
    throw new Error('Cannot reach the backend server at ' + API_BASE);
  }
}
