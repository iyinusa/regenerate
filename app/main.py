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
from app.core.logging import setup_logging

# Setup logging first
setup_logging()

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
    logger.warning("Immersive audio directory not found")

# Mount generated videos
videos_path = Path("app/static/videos")
videos_path.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(videos_path)), name="videos")

# Mount frontend static # This part is tricky if SPA routing is needed, usually handled by catching all else
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
                    background: linear-gradient(135deg, var(--accent-blue), #7c3aed);
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
                    color: var(--accent-blue);
                    font-family: monospace;
                }
                .info-box {
                    background: rgba(31, 74, 174, 0.1);
                    border: 1px solid var(--accent-blue);
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
                    <a href="/docs" style="color: var(--accent-blue); text-decoration: none; font-weight: 600;">📚 View API Documentation</a>
                </p>
            </div>
        </body>
        </html>
        """)

# Catch-all for frontend routes (SPA routing)
@app.get("/{path:path}")
async def serve_frontend_routes(request: Request, path: str):
    """Serve frontend for all other routes - React SPA routing"""
    # Don't intercept API routes
    if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc"):
        return {"detail": "Not found"}
    
    # Check if this is a public profile (username route) and serve with SEO meta tags
    # Username routes don't contain slashes (e.g., /johndoe, not /journey/123)
    if "/" not in path and not path.startswith("regen") and not path.startswith("journey"):
        seo_html = await _get_public_profile_seo_html(path, request)
        if seo_html:
            return HTMLResponse(seo_html)
    
    # Try to serve the built React app's index.html for client-side routing
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    
    # Development fallback
    return await serve_frontend()


async def _get_public_profile_seo_html(username: str, request: Request) -> str | None:
    """Generate HTML with SEO meta tags for public profiles."""
    from app.db.session import get_db
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.user import User, ProfileHistory
    from app.models.privacy import ProfilePrivacy
    
    try:
        async for db in get_db():
            # Find user by username
            result = await db.execute(
                select(User)
                .options(selectinload(User.privacy_settings))
                .where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            privacy = user.privacy_settings
            if not privacy or not privacy.is_public:
                return None
            
            # Get latest profile history
            result = await db.execute(
                select(ProfileHistory)
                .where(ProfileHistory.user_id == user.id)
                .order_by(ProfileHistory.created_at.desc())
                .limit(1)
            )
            history = result.scalar_one_or_none()
            
            if not history or not history.structured_data:
                return None
            
            structured_data = history.structured_data
            
            # Extract profile info for SEO
            name = structured_data.get('name', username)
            title = structured_data.get('title', 'Professional')
            bio = structured_data.get('bio', structured_data.get('summary', ''))
            
            # Get passport image
            passport_url = structured_data.get('passport', structured_data.get('photo', ''))
            
            # Get documentary video
            documentary = structured_data.get('documentary', {})
            full_video = history.full_video or ''
            intro_video = history.intro_video or ''
            video_url = full_video or intro_video or ''
            
            # Build description
            if bio:
                description = bio[:200] + '...' if len(bio) > 200 else bio
            else:
                description = f"Explore {name}'s professional journey on reGen"
            
            # Get the base URL
            base_url = str(request.base_url).rstrip('/')
            page_url = f"{base_url}/{username}"
            
            # Generate SEO HTML
            seo_html = _generate_seo_html(
                title=f"{name} | reGen",
                description=description,
                page_url=page_url,
                image_url=passport_url,
                video_url=video_url,
                author_name=name,
                author_title=title
            )
            
            return seo_html
            
    except Exception as e:
        logger.error(f"Error generating SEO HTML for {username}: {e}")
        return None
    
    return None


def _generate_seo_html(
    title: str,
    description: str,
    page_url: str,
    image_url: str = '',
    video_url: str = '',
    author_name: str = '',
    author_title: str = ''
) -> str:
    """Generate an HTML page with proper SEO meta tags that bootstraps the React app."""
    # Read the original index.html
    index_file = frontend_dist / "index.html"
    
    if index_file.exists():
        original_html = index_file.read_text()
        
        # Build meta tags
        meta_tags = f'''
    <title>{title}</title>
    <meta name="description" content="{description}" />
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="profile" />
    <meta property="og:url" content="{page_url}" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{description}" />
    <meta property="og:site_name" content="reGen" />'''
        
        if image_url:
            meta_tags += f'''
    <meta property="og:image" content="{image_url}" />
    <meta property="og:image:alt" content="{author_name}'s profile photo" />'''
        
        if video_url:
            meta_tags += f'''
    <meta property="og:video" content="{video_url}" />
    <meta property="og:video:type" content="video/mp4" />
    <meta property="og:video:width" content="1920" />
    <meta property="og:video:height" content="1080" />'''
        
        # Twitter Card meta tags
        meta_tags += f'''
    
    <!-- Twitter -->
    <meta name="twitter:card" content="{'player' if video_url else 'summary_large_image'}" />
    <meta name="twitter:url" content="{page_url}" />
    <meta name="twitter:title" content="{title}" />
    <meta name="twitter:description" content="{description}" />'''
        
        if image_url:
            meta_tags += f'''
    <meta name="twitter:image" content="{image_url}" />'''
        
        if video_url:
            meta_tags += f'''
    <meta name="twitter:player" content="{video_url}" />
    <meta name="twitter:player:width" content="1920" />
    <meta name="twitter:player:height" content="1080" />'''
        
        # Profile-specific meta tags
        if author_name:
            meta_tags += f'''
    
    <!-- Profile -->
    <meta property="profile:first_name" content="{author_name.split()[0] if author_name else ''}" />
    <meta property="profile:username" content="{page_url.split('/')[-1]}" />'''
        
        # Inject meta tags by replacing the existing title tag
        # Find and replace the <title>...</title> in the original HTML
        import re
        modified_html = re.sub(
            r'<title>.*?</title>',
            meta_tags,
            original_html,
            count=1,
            flags=re.DOTALL
        )
        
        return modified_html
    
    # Fallback HTML if index.html doesn't exist
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    {meta_tags if 'meta_tags' in dir() else ''}
    <title>{title}</title>
    <meta name="description" content="{description}" />
</head>
<body>
    <div id="root"></div>
    <script>window.location.href = "{page_url}";</script>
</body>
</html>'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )