/**
 * IDTCC Backend API client.
 * Works against the FastAPI backend running at VITE_API_URL (default: http://localhost:8000).
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function _json(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => 'unknown error');
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  /** GET /health */
  health: () => _json('/health'),

  /** GET /api/v1/config */
  config: () => _json('/api/v1/config'),

  /** GET /api/v1/simulation/locations */
  locations: () => _json('/api/v1/simulation/locations'),

  /**
   * POST /api/v1/simulation/run
   * Runs the full 7-agent LangGraph pipeline and returns forecast.
   * @param {Object} params - SimulationRequest
   */
  runSimulation: (params) =>
    _json('/api/v1/simulation/run', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /**
   * POST /api/v1/simulation/stream
   * Returns a native EventSource-compatible URL for SSE streaming.
   * Because EventSource doesn't support POST, we use fetch with ReadableStream.
   */
  streamSimulation: async function* (params, onEvent) {
    const res = await fetch(`${BASE_URL}/api/v1/simulation/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) throw new Error(`Stream API ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() ?? '';
      for (const chunk of lines) {
        const line = chunk.replace(/^data:\s*/, '').trim();
        if (!line) continue;
        try {
          const event = JSON.parse(line);
          onEvent(event);
          yield event;
        } catch {/* ignore malformed chunks */}
      }
    }
  },

  /**
   * GET /api/v1/twins
   * @param {Object} params - query params
   */
  getTwins: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return _json(`/api/v1/twins${qs ? '?' + qs : ''}`);
  },
};

export default api;
