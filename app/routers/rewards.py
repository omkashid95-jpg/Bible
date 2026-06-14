import uuid
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import math
from typing import Optional
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/rewards", tags=["Rewards"])

@router.get("", response_model=schemas.RewardsResponse)
async def get_rewards(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    base_query = select(models.Reward).filter(models.Reward.status == True)
    
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    
    query = base_query.order_by(models.Reward.points_required.asc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rewards = result.scalars().all()
    
    # Get all claimed rewards for user
    claimed_query = select(models.RewardClaim.reward_uuid).filter(models.RewardClaim.user_id == current_user.id)
    claimed_result = await db.execute(claimed_query)
    claimed_reward_uuids = set(claimed_result.scalars().all())
    
    current_points = current_user.total_points
    
    data = []
    for reward in rewards:
        is_claimed = reward.reward_uuid in claimed_reward_uuids
        is_claimable = (not is_claimed) and (current_points >= reward.points_required)
        
        data.append({
            "reward_uuid": reward.reward_uuid,
            "reward_name": reward.reward_name,
            "reward_description": reward.reward_description,
            "reward_type": reward.reward_type,
            "points_required": reward.points_required,
            "is_claimed": is_claimed,
            "is_claimable": is_claimable
        })
        
    return {
        "success": True,
        "current_points": current_points,
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@router.post("/claim", response_model=schemas.ClaimRewardResponse)
async def claim_reward(
    request: schemas.ClaimRewardRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    reward_query = select(models.Reward).filter(models.Reward.reward_uuid == request.reward_uuid, models.Reward.status == True)
    reward_result = await db.execute(reward_query)
    reward = reward_result.scalars().first()
    
    if not reward:
        return JSONResponse(status_code=400, content={"success": False, "message": "Reward not found or inactive"})
        
    claim_query = select(models.RewardClaim).filter(
        models.RewardClaim.reward_uuid == request.reward_uuid,
        models.RewardClaim.user_id == current_user.id
    )
    claim_result = await db.execute(claim_query)
    if claim_result.scalars().first():
        return JSONResponse(status_code=409, content={"success": False, "message": "Reward already claimed"})
        
    if current_user.total_points < reward.points_required:
        return JSONResponse(status_code=400, content={"success": False, "message": "Insufficient points"})
        
    new_claim = models.RewardClaim(
        claim_uuid=f"claim_{uuid.uuid4().hex}",
        reward_uuid=request.reward_uuid,
        user_id=current_user.id,
        claim_status="claimed"
    )
    db.add(new_claim)
    await db.commit()
    await db.refresh(new_claim)
    
    return {
        "success": True,
        "message": "Reward claimed successfully",
        "data": {
            "claim_uuid": new_claim.claim_uuid,
            "reward_uuid": new_claim.reward_uuid,
            "reward_name": reward.reward_name,
            "claimed_at": new_claim.claimed_at
        }
    }

@router.get("/history", response_model=schemas.RewardHistoryResponse)
async def get_reward_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    count_query = select(func.count()).select_from(models.RewardClaim).filter(models.RewardClaim.user_id == current_user.id)
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    
    query = (
        select(models.RewardClaim, models.Reward)
        .join(models.Reward, models.RewardClaim.reward_uuid == models.Reward.reward_uuid)
        .filter(models.RewardClaim.user_id == current_user.id)
        .order_by(models.RewardClaim.claimed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for claim, reward in rows:
        data.append({
            "claim_uuid": claim.claim_uuid,
            "reward_uuid": reward.reward_uuid,
            "reward_name": reward.reward_name,
            "reward_type": reward.reward_type,
            "claimed_at": claim.claimed_at,
            "claim_status": claim.claim_status
        })
        
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }
