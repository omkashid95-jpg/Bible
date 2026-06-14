from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, models, dependencies, database

router = APIRouter(prefix="/api/v1/home", tags=["Home Dashboard"])

@router.get("/dashboard", response_model=schemas.HomeDashboardResponse)
async def get_home_dashboard(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Map dynamic data from the authenticated user model
    user_data = {
        "id": current_user.uuid,
        "full_name": current_user.full_name,
        "profile_image": current_user.profile_image or "",
        "rank": current_user.current_rank,
        "level": current_user.current_level,
        "points": current_user.total_points,
        "daily_streak": current_user.daily_streak
    }
    
    # Map static fallback data for today's challenge 
    # (Pending future dynamic challenge DB schemas)
    challenge_data = {
        "challenge_id": "ch_001",
        "title": "Think Better. Choose Better.",
        "description": "Answer mindset based questions and improve your daily thinking habits.",
        "progress": 0.0
    }
    
    return {
        "user": user_data,
        "today_challenge": challenge_data
    }
