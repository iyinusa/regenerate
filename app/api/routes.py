"""Main API router that combines all route modules."""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.profile import router as profile_router
from app.api.websocket import ws_manager, websocket_callback_factory
from app.services.task_orchestrator import task_orchestrator

logger = logging.getLogger(__name__)

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(profile_router)


# WebSocket endpoint for real-time task updates
@api_router.websocket("/ws/tasks/{job_id}")
async def websocket_task_updates(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for receiving real-time task updates.
    
    Clients connect to this endpoint with a job_id to receive
    live updates on task progress, completion, and failures.
    
    Args:
        websocket: The WebSocket connection
        job_id: The job ID to subscribe to updates for
    """
    from app.services.profile_service import profile_jobs
    
    # Check if job exists before accepting connection
    if job_id not in profile_jobs:
        # Try to check in task orchestrator as well
        plan = task_orchestrator.get_plan(job_id)
        if not plan:
            await websocket.close(code=4004, reason="Job not found")
            return
    
    connection = None
    try:
        connection = await ws_manager.connect(websocket, job_id)
        
        # Register a callback with the task orchestrator for this job
        callback = await websocket_callback_factory(job_id)
        task_orchestrator.register_callback(job_id, callback)
        
        try:
            # Send initial status if plan exists
            plan_status = task_orchestrator.get_plan_status(job_id)
            if plan_status:
                await ws_manager.send_plan_update(job_id, "initial_status", plan_status)
            
            # Keep connection alive and handle incoming messages
            while True:
                try:
                    # Wait for messages (ping/pong or commands)
                    data = await websocket.receive_text()
                    
                    # Handle ping
                    if data == "ping":
                        await websocket.send_text("pong")
                    
                    # Handle status request
                    elif data == "status":
                        status = task_orchestrator.get_plan_status(job_id)
                        if status:
                            await ws_manager.send_plan_update(job_id, "status_response", status)
                            
                except WebSocketDisconnect:
                    break
                    
        except Exception as e:
            logger.error(f"Error in WebSocket message loop for job {job_id}: {e}")
        finally:
            # Cleanup
            task_orchestrator.unregister_callback(job_id, callback)
            await ws_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket connection error for job {job_id}: {e}")
        if connection is None:
            # Connection wasn't established, try to close websocket manually
            try:
                await websocket.close()
            except:
                pass


# Health check endpoint
@api_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "reGen API"}


@api_router.get("/ws/stats", tags=["websocket"])
async def websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "total_connections": ws_manager.get_connection_count(),
        "active_jobs": ws_manager.get_active_jobs()
    }


@api_router.post("/admin/cleanup-jobs", tags=["admin"])
async def cleanup_jobs():
    """Manually trigger cleanup of old completed jobs."""
    from app.services.profile_service import profile_service
    
    try:
        profile_service.cleanup_completed_jobs(max_age_minutes=5)  # Clean jobs older than 5 minutes
        return {"message": "Job cleanup completed successfully"}
    except Exception as e:
        logger.error(f"Manual job cleanup failed: {e}")
        return {"error": f"Cleanup failed: {str(e)}"}


@api_router.get("/admin/job-stats", tags=["admin"])
async def get_job_stats():
    """Get current job statistics."""
    from app.services.profile_service import profile_service
    
    try:
        stats = profile_service.get_job_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get job stats: {e}")
        return {"error": f"Failed to get job stats: {str(e)}"}