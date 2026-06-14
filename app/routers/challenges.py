from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, models, dependencies, database

router = APIRouter(prefix="/api/v1/challenges", tags=["Challenges"])

@router.get("/today", response_model=schemas.TodayChallengeDetails)
async def get_todays_challenge(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Returning mocked static data for now, pending a Challenges Database Architecture
    return {
        "challenge_id": "ch_001",
        "title": "Think Better. Choose Better.",
        "description": "Answer mindset based questions",
        "total_questions": 10,
        "reward_points": 20
    }
