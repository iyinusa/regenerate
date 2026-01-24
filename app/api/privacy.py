from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.core.dependencies import get_current_user_required
from app.models.user import User, ProfileHistory
from app.models.privacy import ProfilePrivacy
from app.schemas.privacy import PrivacyResponse, PrivacyUpdate

router = APIRouter(prefix="/privacy", tags=["privacy"])

@router.get("/", response_model=PrivacyResponse)
async def get_privacy_settings(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's privacy settings."""
    result = await db.execute(
        select(ProfilePrivacy).where(ProfilePrivacy.user_id == current_user.id)
    )
    privacy = result.scalar_one_or_none()
    
    if not privacy:
        # Create default privacy settings if not exists
        privacy = ProfilePrivacy(user_id=current_user.id)
        db.add(privacy)
        await db.commit()
        await db.refresh(privacy)
    
    response = PrivacyResponse(
        is_public=privacy.is_public,
        hidden_sections=privacy.hidden_sections or {},
        user_id=current_user.id,
        guest_id=current_user.guest_id,
        username=current_user.username
    )
    return response

@router.put("/", response_model=PrivacyResponse)
async def update_privacy_settings(
    update_data: PrivacyUpdate,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Update privacy settings and username."""
    # Check if username is changing and valid
    if update_data.username and update_data.username != current_user.username:
        # Check uniqueness
        result = await db.execute(select(User).where(User.username == update_data.username))
        existing_user = result.scalar_one_or_none()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        current_user.username = update_data.username
        db.add(current_user)

    # Update Privacy
    result = await db.execute(
        select(ProfilePrivacy).where(ProfilePrivacy.user_id == current_user.id)
    )
    privacy = result.scalar_one_or_none()
    
    if not privacy:
        privacy = ProfilePrivacy(user_id=current_user.id)
        db.add(privacy)
    
    privacy.is_public = update_data.is_public
    privacy.hidden_sections = update_data.hidden_sections
    
    await db.commit()
    await db.refresh(privacy)
    
    return PrivacyResponse(
        is_public=privacy.is_public,
        hidden_sections=privacy.hidden_sections or {},
        user_id=current_user.id,
        guest_id=current_user.guest_id,
        username=current_user.username
    )

@router.get("/public/{username}")
async def get_public_profile(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get public profile data if enabled."""
    # Find user
    result = await db.execute(
        select(User)
        .options(selectinload(User.privacy_settings))
        .where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    privacy = user.privacy_settings
    
    if not privacy or not privacy.is_public:
        raise HTTPException(status_code=404, detail="Profile is private or not found")
        
    # Get latest profile history
    result = await db.execute(
        select(ProfileHistory)
        .where(ProfileHistory.user_id == user.id)
        .order_by(ProfileHistory.created_at.desc())
        .limit(1)
    )
    history = result.scalar_one_or_none()
    
    if not history or not history.structured_data:
        raise HTTPException(status_code=404, detail="No profile data found")
        
    # Extract the structured data
    structured_data = history.structured_data.copy()
    
    # Filter hidden sections
    hidden = privacy.hidden_sections or {}
    
    # The structured_data contains the profile data at the root level,
    # plus journey, timeline, and documentary data
    profile_data = {k: v for k, v in structured_data.items() 
                   if k not in ['journey', 'timeline', 'documentary', 'generated_at', 'generation_status']}
    
    # Create response structure similar to what Journey page expects
    response = {
        "profile": profile_data,
        "journey": structured_data.get("journey", {}),
        "timeline": structured_data.get("timeline", {}),
        "documentary": structured_data.get("documentary", {}),
        "intro_video": history.intro_video,
        "full_video": history.full_video,
        "history_id": None  # Don't expose for public profiles
    }
    
    # Filter sections based on privacy settings
    if hidden.get("chronicles"):
        response["timeline"] = {}
         
    if hidden.get("experience") and "experiences" in response["profile"]:
        del response["profile"]["experiences"]
         
    if hidden.get("projects") and "projects" in response["profile"]:
        del response["profile"]["projects"]
    
    # Additional sections
    if hidden.get("skills") and "skills" in response["profile"]:
        del response["profile"]["skills"]

    if hidden.get("education") and "education" in response["profile"]:
        del response["profile"]["education"]

    return response
