"""WebSocket Manager for Real-time Task Updates.

This module provides WebSocket support for broadcasting real-time
task progress updates to connected frontend clients.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents a WebSocket connection."""
    websocket: WebSocket
    job_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    
    def __hash__(self):
        """Make Connection hashable by using websocket object id and job_id."""
        return hash((id(self.websocket), self.job_id))
    
    def __eq__(self, other):
        """Equality based on websocket object identity and job_id."""
        if not isinstance(other, Connection):
            return False
        return id(self.websocket) == id(other.websocket) and self.job_id == other.job_id
    
    async def send(self, data: Dict[str, Any]) -> bool:
        """Send data to the WebSocket."""
        try:
            await self.websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Failed to send to WebSocket: {e}")
            return False


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        # Map of job_id -> set of connections
        self._connections: Dict[str, Set[Connection]] = {}
        # Map of connection -> job_id for reverse lookup
        self._connection_jobs: Dict[WebSocket, str] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, job_id: str) -> Connection:
        """Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket to accept
            job_id: The job ID to subscribe to
            
        Returns:
            Connection object
        """
        await websocket.accept()
        
        connection = Connection(websocket=websocket, job_id=job_id)
        
        async with self._lock:
            if job_id not in self._connections:
                self._connections[job_id] = set()
            self._connections[job_id].add(connection)
            self._connection_jobs[websocket] = job_id
        
        logger.info(f"WebSocket connected for job {job_id}. Total connections: {len(self._connections.get(job_id, set()))}")
        
        # Send initial connection confirmation
        await connection.send({
            "event": "connected",
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to task updates stream"
        })
        
        return connection
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection.
        
        Args:
            websocket: The disconnected WebSocket
        """
        async with self._lock:
            job_id = self._connection_jobs.pop(websocket, None)
            
            if job_id and job_id in self._connections:
                # Find and remove the connection
                to_remove = None
                for conn in self._connections[job_id]:
                    if conn.websocket == websocket:
                        to_remove = conn
                        break
                
                if to_remove:
                    self._connections[job_id].discard(to_remove)
                
                # Clean up empty sets
                if not self._connections[job_id]:
                    del self._connections[job_id]
                
                logger.info(f"WebSocket disconnected from job {job_id}")
    
    async def broadcast(self, job_id: str, data: Dict[str, Any]) -> int:
        """Broadcast data to all connections for a job.
        
        Args:
            job_id: The job ID to broadcast to
            data: The data to send
            
        Returns:
            Number of successful sends
        """
        connections = self._connections.get(job_id, set())
        if not connections:
            return 0
        
        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow().isoformat()
        
        success_count = 0
        failed_connections = []
        
        for conn in connections:
            if await conn.send(data):
                success_count += 1
            else:
                failed_connections.append(conn)
        
        # Clean up failed connections
        if failed_connections:
            async with self._lock:
                for conn in failed_connections:
                    self._connections.get(job_id, set()).discard(conn)
                    self._connection_jobs.pop(conn.websocket, None)
        
        return success_count
    
    async def send_task_update(
        self,
        job_id: str,
        event: str,
        task_data: Dict[str, Any],
        plan_progress: Optional[int] = None
    ) -> int:
        """Send a task update to subscribers.
        
        Args:
            job_id: The job ID
            event: Event type (task_started, task_progress, task_completed, etc.)
            task_data: Task information
            plan_progress: Overall plan progress (0-100)
            
        Returns:
            Number of clients notified
        """
        data = {
            "event": event,
            "job_id": job_id,
            "task": task_data,
        }
        
        if plan_progress is not None:
            data["plan_progress"] = plan_progress
        
        return await self.broadcast(job_id, data)
    
    async def send_plan_update(
        self,
        job_id: str,
        event: str,
        plan_data: Dict[str, Any]
    ) -> int:
        """Send a plan-level update to subscribers.
        
        Args:
            job_id: The job ID
            event: Event type (plan_started, plan_completed, plan_failed)
            plan_data: Plan information
            
        Returns:
            Number of clients notified
        """
        data = {
            "event": event,
            "job_id": job_id,
            "plan": plan_data,
        }
        
        return await self.broadcast(job_id, data)
    
    def get_connection_count(self, job_id: str = None) -> int:
        """Get the number of active connections.
        
        Args:
            job_id: Optional job ID to filter by
            
        Returns:
            Number of connections
        """
        if job_id:
            return len(self._connections.get(job_id, set()))
        return sum(len(conns) for conns in self._connections.values())
    
    def get_active_jobs(self) -> list:
        """Get list of job IDs with active connections."""
        return list(self._connections.keys())


# Global WebSocket manager instance
ws_manager = WebSocketManager()


async def websocket_callback_factory(job_id: str):
    """Create a callback function for the task orchestrator to use.
    
    This factory creates a callback that the task orchestrator can
    register to receive updates and forward them to WebSocket clients.
    
    Args:
        job_id: The job ID
        
    Returns:
        Async callback function
    """
    async def callback(update: Dict[str, Any]):
        event_type = update.get("event", "update")
        data = update.get("data", {})
        
        if isinstance(data, dict) and "task" in data:
            await ws_manager.send_task_update(
                job_id=job_id,
                event=event_type,
                task_data=data["task"],
                plan_progress=data.get("plan_progress")
            )
        else:
            await ws_manager.broadcast(job_id, update)
    
    return callback
