"""
reGen FastAPI Application

This is the main entry point for the reGen application that helps regenerate
and tell professional stories better using AI.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import logging

# Import routers
from app.api.routes import api_router
from app.services.profile_service import profile_service

# Configure logging
logger = logging.getLogger(__name__)

# Global variable to control cleanup task
cleanup_task = None

async def cleanup_jobs_periodically():
    """Background task to clean up old completed jobs periodically."""
    while True:
        try:
            # Clean up jobs older than 30 minutes
            profile_service.cleanup_completed_jobs(max_age_minutes=30)
            # Run every 10 minutes
            await asyncio.sleep(600)
        except Exception as e:
            logger.error(f"Error in background cleanup task: {e}")
            await asyncio.sleep(600)  # Still wait before retrying

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global cleanup_task
    cleanup_task = asyncio.create_task(cleanup_jobs_periodically())
    logger.info("Started background job cleanup task")
    
    yield
    
    # Shutdown
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped background job cleanup task")

# Create FastAPI application
app = FastAPI(
    title="reGen API",
    description="reGen helps regenerate and tells your journey better using smart AI to analyse professional contributions and create compelling narratives in an immersive cinematic experience.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # WebSocket support
    allow_origin_regex=r"https?://.*",
)

# Include API routes
app.include_router(api_router)

# Mount static files for frontend
frontend_path = Path(__file__).parent.parent / "frontend"
frontend_dist = frontend_path / "dist"

# Mount immersive audio files - check production first, then development
immersive_path_prod = frontend_dist / "immersive"
immersive_path_dev = frontend_path / "public" / "immersive"

if immersive_path_prod.exists():
    app.mount("/immersive", StaticFiles(directory=str(immersive_path_prod)), name="immersive")
    logger.info(f"Mounted production immersive audio files from {immersive_path_prod}")
elif immersive_path_dev.exists():
    app.mount("/immersive", StaticFiles(directory=str(immersive_path_dev)), name="immersive")
    logger.info(f"Mounted development immersive audio files from {immersive_path_dev}")
else:
    logger.warning("No immersive audio files found")

# Try to mount the built React app first (production)
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    # Mount assets directory
    assets_path = frontend_dist / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
    # Mount any other static files from dist
    app.mount("/static", StaticFiles(directory=str(frontend_dist)), name="static")
elif frontend_path.exists():
    # Development mode - mount static files if they exist
    static_path = frontend_path / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# API routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "reGen API"}

@app.get("/favicon.png")
async def favicon():
    """Serve favicon"""
    favicon_file = frontend_dist / "favicon.png"
    if favicon_file.exists():
        return FileResponse(str(favicon_file))
    # Fallback to static folder
    favicon_fallback = frontend_path / "static" / "favicon.png"
    if favicon_fallback.exists():
        return FileResponse(str(favicon_fallback))
    return {"detail": "Favicon not found"}

@app.get("/api/v1/test")
async def test_endpoint():
    """Test API endpoint"""
    return {"message": "reGen API is working!", "version": "0.1.0"}

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the React frontend home page"""
    # Try production build first
    index_file = frontend_dist / "index.html"
    
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        # Development fallback - show message to build the frontend
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>reGen - Development</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 40px;
                    background: #000011;
                    color: white;
                    text-align: center;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                }
                .gradient-text {
                    background: linear-gradient(135deg, #00d4ff, #7c3aed);
                    -webkit-background-clip: text;
                    background-clip: text;
                    -webkit-text-fill-color: transparent;
                    font-size: 3rem;
                    margin: 2rem 0;
                }
                code {
                    background: #1a1a2e;
                    padding: 4px 8px;
                    border-radius: 4px;
                    color: #00d4ff;
                    font-family: monospace;
                }
                .info-box {
                    background: rgba(0, 212, 255, 0.1);
                    border: 1px solid #00d4ff;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: left;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="gradient-text">reGen</h1>
                <h2>🚀 API is Running!</h2>
                
                <div class="info-box">
                    <h3>Frontend Development Mode</h3>
                    <p>The React frontend needs to be built. In a separate terminal, run:</p>
                    <pre><code>cd frontend
npm install
npm run dev</code></pre>
                    <p>Then access the frontend at: <strong>http://localhost:5173</strong></p>
                </div>
                
                <div class="info-box">
                    <h3>Production Build</h3>
                    <p>To serve the frontend from this API server, build it first:</p>
                    <pre><code>cd frontend
npm run build</code></pre>
                    <p>The built files will be served automatically from this URL.</p>
                </div>
                
                <p style="margin-top: 40px;">
                    <a href="/docs" style="color: #00d4ff; text-decoration: none; font-weight: 600;">📚 View API Documentation</a>
                </p>
            </div>
        </body>
        </html>
        """)

# Catch-all for frontend routes (SPA routing)
@app.get("/{path:path}")
async def serve_frontend_routes(path: str):
    """Serve frontend for all other routes - React SPA routing"""
    # Don't intercept API routes
    if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc"):
        return {"detail": "Not found"}
    
    # Try to serve the built React app's index.html for client-side routing
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    
    # Development fallback
    return await serve_frontend()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )