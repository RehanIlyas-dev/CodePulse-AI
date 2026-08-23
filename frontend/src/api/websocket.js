const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1';

// --> Connect to WebSocket for job updates
export function connectJobWebSocket(jobId, onMessage, onError) {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs/${jobId}`);

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