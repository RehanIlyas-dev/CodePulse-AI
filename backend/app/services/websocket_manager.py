from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        """Accepts the incoming WebSocket connection and registers it."""
        await websocket.accept()
        self.active_connections[job_id] = websocket

    def disconnect(self, job_id: str):
        """Removes the connection when a client disconnects."""
        if job_id in self.active_connections:
            del self.active_connections[job_id]

    async def send_progress(self, job_id: str, status: str, progress: int, data: dict = None):
        """Pushes a structured progress frame to a connected client."""
        if job_id not in self.active_connections:
            return
        websocket = self.active_connections[job_id]
        payload = {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "data": data
        }
        try:
            await websocket.send_json(payload)
        except Exception:
            # Client disconnected mid-job - stop tracking it, don't fail the job
            self.disconnect(job_id)

# Singleton instance for application-wide access
ws_manager = ConnectionManager()