import { useState, useCallback, useRef } from 'react';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export default function useAgentStream() {
  const [steps, setSteps] = useState([]);
  const [answer, setAnswer] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const reset = useCallback(() => {
    setSteps([]);
    setAnswer('');
    setError(null);
    setIsRunning(false);
  }, []);

  const run = useCallback(async (sessionId, query) => {
    reset();
    setIsRunning(true);

    // fetch + ReadableStream for SSE (needed because body is POST)
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(`${BASE_URL}/api/agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, query, stream: true }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === 'step') {
              setSteps((prev) => [...prev, event]);
            } else if (event.type === 'done') {
              setAnswer(event.answer);
            } else if (event.type === 'error') {
              setError(event.message);
            }
          } catch (_) {}
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Stream connection failed.');
      }
    } finally {
      setIsRunning(false);
    }
  }, [reset]);

  return { steps, answer, isRunning, error, run, reset };
}
