from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
import uuid
import random
import string
import math
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/referrals", tags=["Referrals"])

def generate_code(full_name: str) -> str:
    base = "".join(filter(str.isalpha, full_name)).upper()
    if not base:
        base = "USER"
    base = base[:5]
    suffix = ''.join(random.choices(string.digits, k=3))
    return f"{base}{suffix}"

@router.post("/generate-code", response_model=schemas.GenerateReferralResponse)
async def generate_referral_code(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.Referral).filter(models.Referral.user_id == current_user.id)
    result = await db.execute(query)
    referral = result.scalars().first()
    
    if referral:
        return {
            "success": True,
            "data": {
                "referral_uuid": referral.referral_uuid,
                "referral_code": referral.referral_code,
                "referral_link": referral.referral_link,
                "total_referrals": referral.total_referrals,
                "total_rewards_earned": referral.total_rewards_earned
            }
        }
        
    while True:
        code = generate_code(current_user.full_name or "USER")
        check_query = select(models.Referral).filter(models.Referral.referral_code == code)
        check_result = await db.execute(check_query)
        if not check_result.scalars().first():
            break
            
    referral_link = f"https://app.com/ref/{code}"
    
    new_referral = models.Referral(
        referral_uuid=f"ref_{uuid.uuid4().hex}",
        user_id=current_user.id,
        referral_code=code,
        referral_link=referral_link,
        total_referrals=0,
        total_rewards_earned=0
    )
    db.add(new_referral)
    await db.commit()
    await db.refresh(new_referral)
    
    return {
        "success": True,
        "data": {
            "referral_uuid": new_referral.referral_uuid,
            "referral_code": new_referral.referral_code,
            "referral_link": new_referral.referral_link,
            "total_referrals": new_referral.total_referrals,
            "total_rewards_earned": new_referral.total_rewards_earned
        }
    }

@router.get("/statistics", response_model=schemas.ReferralStatisticsResponse)
async def get_referral_statistics(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.Referral).filter(models.Referral.user_id == current_user.id)
    result = await db.execute(query)
    referral = result.scalars().first()
    
    if not referral:
        return JSONResponse(status_code=404, content={"success": False, "message": "Referral record not found. Please generate a code first."})
        
    return {
        "success": True,
        "data": {
            "referral_code": referral.referral_code,
            "referral_link": referral.referral_link,
            "total_referrals": referral.total_referrals,
            "successful_referrals": referral.successful_referrals,
            "pending_referrals": referral.pending_referrals,
            "total_rewards_earned": referral.total_rewards_earned,
            "total_points_earned": referral.total_points_earned
        }
    }

@router.get("/history", response_model=schemas.ReferralHistoryResponse)
async def get_referral_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    base_query = select(models.ReferralHistory).filter(models.ReferralHistory.referrer_user_id == current_user.id)
    
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    
    query = (
        base_query
        .options(selectinload(models.ReferralHistory.referred))
        .order_by(models.ReferralHistory.registered_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    history_records = result.scalars().all()
    
    data = []
    for record in history_records:
        referred_name = record.referred.full_name if record.referred else "Unknown User"
        data.append({
            "history_uuid": record.history_uuid,
            "referred_user_name": referred_name,
            "status": record.status,
            "reward_points": record.reward_points,
            "registered_at": record.registered_at,
            "rewarded_at": record.rewarded_at
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
