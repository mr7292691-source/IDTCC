/**
 * IDTCC Backend API client.
 *
 * Works against the FastAPI backend at VITE_API_URL (default http://localhost:8000).
 * Hardened for production: per-request timeout, exponential-backoff retry on
 * transient failures, structured error objects, and a resilient SSE reader that
 * survives partial chunks.
 *
 * Response shapes are documented in src/types/api.d.ts (kept in sync with the
 * backend Pydantic models in backend/app/models/schemas.py).
 */

// Default to same-origin ('') so requests are proxied by Vite in dev (see
// vite.config.js) and served same-origin in production. The backend does not
// enable CORS, so absolute cross-origin URLs will be blocked by the browser —
// only set VITE_API_URL when the API is genuinely same-origin or proxied.
const BASE_URL = import.meta.env.VITE_API_URL ?? '';

const DEFAULTS = {
  timeoutMs: 120_000,   // simulations can take a while on first cold call
  retries: 2,           // total attempts = retries + 1
  backoffMs: 600,       // base backoff, doubled each retry
};

/** Structured error so callers can branch on status / retryability. */
export class ApiError extends Error {
  constructor(message, { status = 0, body = null, retryable = false } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
    this.retryable = retryable;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** A 5xx, 429, or network/timeout failure is worth retrying; 4xx is not. */
function isRetryableStatus(status) {
  return status === 0 || status === 429 || (status >= 500 && status <= 599);
}

async function _fetch(path, options = {}, cfg = {}) {
  const { timeoutMs, retries, backoffMs } = { ...DEFAULTS, ...cfg };
  let lastErr;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        signal: controller.signal,
        ...options,
      });
      clearTimeout(timer);

      if (!res.ok) {
        const body = await res.text().catch(() => '');
        const err = new ApiError(`API ${res.status}: ${body || res.statusText}`, {
          status: res.status,
          body,
          retryable: isRetryableStatus(res.status),
        });
        if (err.retryable && attempt < retries) {
          lastErr = err;
          await sleep(backoffMs * 2 ** attempt);
          continue;
        }
        throw err;
      }
      return res;
    } catch (e) {
      clearTimeout(timer);
      // AbortError (timeout) and network errors are retryable.
      const networkErr =
        e instanceof ApiError
          ? e
          : new ApiError(
              e.name === 'AbortError' ? `Request timed out after ${timeoutMs}ms` : e.message,
              { status: 0, retryable: true },
            );
      if (networkErr.retryable && attempt < retries) {
        lastErr = networkErr;
        await sleep(backoffMs * 2 ** attempt);
        continue;
      }
      throw networkErr;
    }
  }
  throw lastErr ?? new ApiError('Request failed', { status: 0, retryable: true });
}

async function _json(path, options = {}, cfg = {}) {
  const res = await _fetch(path, options, cfg);
  return res.json();
}

export const api = {
  /** GET /health */
  health: () => _json('/health', {}, { retries: 0, timeoutMs: 4000 }),

  /** GET /health/ready */
  ready: () => _json('/health/ready', {}, { retries: 0, timeoutMs: 4000 }),

  /** GET /api/v1/config */
  config: () => _json('/api/v1/config'),

  /** GET /api/v1/metrics/summary — per-agent latency, tokens, success rate */
  metricsSummary: () => _json('/api/v1/metrics/summary', {}, { retries: 1, timeoutMs: 5000 }),

  /** GET /api/v1/simulation/locations */
  locations: () => _json('/api/v1/simulation/locations'),

  /** GET /api/v1/simulation/locations/:code */
  locationDetail: (code) => _json(`/api/v1/simulation/locations/${code.toUpperCase()}`),

  /**
   * POST /api/v1/simulation/run — full 7-agent LangGraph pipeline (sync).
   * @param {import('../types/api').SimulationRequest} params
   * @returns {Promise<import('../types/api').ForecastResponse>}
   */
  runSimulation: (params) =>
    _json('/api/v1/simulation/run', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /**
   * POST /api/v1/simulation/stream — Server-Sent Events.
   * EventSource doesn't support POST, so we read the body stream manually.
   * Yields each parsed event AND invokes onEvent(event) for imperative callers.
   */
  streamSimulation: async function* (params, onEvent = () => {}) {
    const res = await _fetch(
      '/api/v1/simulation/stream',
      { method: 'POST', body: JSON.stringify(params) },
      { retries: 0, timeoutMs: 180_000 }, // streaming: don't retry mid-stream
    );

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split('\n\n');
      buffer = chunks.pop() ?? '';
      for (const chunk of chunks) {
        const line = chunk.replace(/^data:\s*/, '').trim();
        if (!line) continue;
        try {
          const event = JSON.parse(line);
          onEvent(event);
          yield event;
        } catch {
          /* ignore malformed/partial chunks */
        }
      }
    }
  },

  /** GET /api/v1/twins */
  getTwins: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return _json(`/api/v1/twins${qs ? '?' + qs : ''}`);
  },
};

export default api;
