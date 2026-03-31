const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || body.error || detail;
    } catch (_) {}
    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }
  return response.json();
}

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/api/upload', { method: 'POST', body: formData });
}

export async function askQuestion(sessionId, question) {
  return request('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question }),
  });
}

export async function runAgent(sessionId, query) {
  return request('/api/agent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, query, stream: false }),
  });
}

export function createAgentStream(sessionId, query) {
  const url = `${BASE_URL}/api/agent`;
  return { sessionId, query, url };
}
