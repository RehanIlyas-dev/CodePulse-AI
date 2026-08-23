import { getToken } from './client';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1';

// --> Connect to WebSocket for job updates (token via query param — browsers can't set WS headers)
export function connectJobWebSocket(jobId, onMessage, onError) {
  const token = getToken();
  const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs/${jobId}?token=${encodeURIComponent(token || '')}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data); // Parse the incoming message as JSON
      onMessage(data);
    } catch (err) {
      console.error('Failed to parse WS message:', err);
    }
  };
  // --> Handle WebSocket errors
  ws.onerror = (event) => {
    if (onError) onError(event);
  };

  return ws;
}