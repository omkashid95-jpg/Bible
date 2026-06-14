from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/profile", tags=["Profile Management"])

@router.get("", response_model=schemas.UserProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    global_rank_query = select(func.count()).filter(models.User.total_points > current_user.total_points)
    global_rank = (await db.execute(global_rank_query)).scalar() + 1
    
    lang_rank_query = select(func.count()).filter(
        models.User.total_points > current_user.total_points,
        models.User.primary_language == current_user.primary_language
    )
    lang_rank = (await db.execute(lang_rank_query)).scalar() + 1
    
    quiz_stats_query = select(
        func.count(models.QuizHistory.id).label("total_played"),
        func.sum(models.QuizHistory.correct_answers).label("total_correct"),
        func.sum(models.QuizHistory.total_questions).label("total_questions")
    ).filter(models.QuizHistory.user_id == current_user.id)
    
    quiz_stats = (await db.execute(quiz_stats_query)).one()
    total_quizzes_played = quiz_stats.total_played or 0
    total_correct_answers = int(quiz_stats.total_correct or 0)
    total_qs = quiz_stats.total_questions or 0
    accuracy_percentage = (total_correct_answers / total_qs * 100.0) if total_qs > 0 else 0.0
    
    referral_query = select(models.Referral.total_referrals).filter(models.Referral.user_id == current_user.id)
    total_referrals = (await db.execute(referral_query)).scalar() or 0
    
    reward_query = select(func.count()).filter(models.RewardClaim.user_id == current_user.id)
    total_rewards_claimed = (await db.execute(reward_query)).scalar() or 0
    
    submissions_query = select(func.count()).filter(models.QuizSubmission.user_id == current_user.id)
    total_created_quizzes = (await db.execute(submissions_query)).scalar() or 0
    
    translations_query = select(func.count()).filter(models.QuizTranslation.translator_user_id == current_user.id)
    total_translations = (await db.execute(translations_query)).scalar() or 0
    
    corrections_query = select(func.count()).filter(models.QuizCorrection.user_id == current_user.id)
    total_corrections = (await db.execute(corrections_query)).scalar() or 0
    
    data = {
        "user_uuid": current_user.uuid,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "country_code": current_user.country_code,
        "profile_image": current_user.profile_image,
        "primary_language": current_user.primary_language,
        "age": current_user.age,
        "gender": current_user.gender,
        "education": current_user.education,
        "total_points": current_user.total_points,
        "current_level": current_user.current_level,
        "daily_streak": current_user.daily_streak,
        "global_rank": global_rank,
        "language_rank": lang_rank,
        "total_quizzes_played": total_quizzes_played,
        "total_correct_answers": total_correct_answers,
        "accuracy_percentage": round(accuracy_percentage, 2),
        "total_referrals": total_referrals,
        "total_rewards_claimed": total_rewards_claimed,
        "total_created_quizzes": total_created_quizzes,
        "total_translations": total_translations,
        "total_corrections": total_corrections,
        "member_since": current_user.created_at
    }
    
    return {
        "success": True,
        "data": data
    }

@router.put("", response_model=schemas.UpdateProfileResponse)
async def update_profile(
    request: schemas.UpdateProfileRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.profile_image is not None:
        current_user.profile_image = request.profile_image
    if request.age is not None:
        current_user.age = request.age
    if request.gender is not None:
        if request.gender not in ["Male", "Female", "Other"]:
            return JSONResponse(status_code=400, content={"success": False, "message": "Invalid gender value"})
        current_user.gender = request.gender
    if request.education is not None:
        current_user.education = request.education
        
    if request.primary_language_id is not None:
        lang_query = select(models.Language).filter(models.Language.id == request.primary_language_id)
        lang_result = await db.execute(lang_query)
        lang = lang_result.scalars().first()
        if not lang:
            return JSONResponse(status_code=400, content={"success": False, "message": "Language not found"})
        current_user.primary_language = lang.name
        
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": {
            "full_name": current_user.full_name,
            "profile_image": current_user.profile_image,
            "age": current_user.age,
            "gender": current_user.gender,
            "education": current_user.education,
            "primary_language": current_user.primary_language
        }
    }

@router.get("/achievements", response_model=schemas.ProfileAchievementsResponse)
async def get_profile_achievements(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    achievements_query = select(models.Achievement)
    achievements_result = await db.execute(achievements_query)
    achievements = achievements_result.scalars().all()
    
    user_achievements_query = select(models.UserAchievement).filter(models.UserAchievement.user_id == current_user.id)
    user_achievements_result = await db.execute(user_achievements_query)
    user_achievements = user_achievements_result.scalars().all()
    
    earned_map = {ua.achievement_uuid: ua.earned_at for ua in user_achievements}
    
    data = []
    for ach in achievements:
        is_earned = ach.achievement_uuid in earned_map
        earned_at = earned_map.get(ach.achievement_uuid)
        
        data.append({
            "achievement_uuid": ach.achievement_uuid,
            "achievement_name": ach.achievement_name,
            "achievement_description": ach.achievement_description,
            "achievement_icon": ach.achievement_icon,
            "achievement_type": ach.achievement_type,
            "is_earned": is_earned,
            "earned_at": earned_at
        })
        
    return {
        "success": True,
        "summary": {
            "total_achievements": len(achievements),
            "earned_achievements": len(earned_map)
        },
        "data": data
    }

@router.get("/achievements/{achievement_uuid}", response_model=schemas.AchievementDetailResponse)
async def get_achievement_details(
    achievement_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.Achievement).filter(models.Achievement.achievement_uuid == achievement_uuid)
    result = await db.execute(query)
    ach = result.scalars().first()
    
    if not ach:
        return JSONResponse(status_code=404, content={"success": False, "message": "Achievement not found"})
        
    ua_query = select(models.UserAchievement).filter(
        models.UserAchievement.user_id == current_user.id,
        models.UserAchievement.achievement_uuid == achievement_uuid
    )
    ua_result = await db.execute(ua_query)
    user_ach = ua_result.scalars().first()
    
    is_earned = user_ach is not None
    earned_at = user_ach.earned_at if user_ach else None
    
    current_progress = 0
    if ach.achievement_type == "quiz":
        q_count = select(func.count(models.QuizHistory.id)).filter(models.QuizHistory.user_id == current_user.id)
        current_progress = (await db.execute(q_count)).scalar() or 0
    elif ach.achievement_type == "translation":
        t_count = select(func.count(models.QuizTranslation.id)).filter(models.QuizTranslation.translator_user_id == current_user.id)
        current_progress = (await db.execute(t_count)).scalar() or 0
    elif ach.achievement_type == "correction":
        c_count = select(func.count(models.QuizCorrection.id)).filter(models.QuizCorrection.user_id == current_user.id)
        current_progress = (await db.execute(c_count)).scalar() or 0
    elif ach.achievement_type == "referral":
        r_query = select(models.Referral.total_referrals).filter(models.Referral.user_id == current_user.id)
        current_progress = (await db.execute(r_query)).scalar() or 0
    elif ach.achievement_type == "streak":
        current_progress = current_user.daily_streak
    elif ach.achievement_type == "reward":
        rew_query = select(func.count(models.RewardClaim.id)).filter(models.RewardClaim.user_id == current_user.id)
        current_progress = (await db.execute(rew_query)).scalar() or 0
    elif ach.achievement_type == "leaderboard":
        current_progress = current_user.total_points
        
    if current_progress > ach.required_value:
        current_progress = ach.required_value
        
    progress_percentage = int((current_progress / ach.required_value) * 100) if ach.required_value > 0 else 0
    
    return {
        "success": True,
        "data": {
            "achievement_uuid": ach.achievement_uuid,
            "achievement_name": ach.achievement_name,
            "achievement_description": ach.achievement_description,
            "achievement_icon": ach.achievement_icon,
            "achievement_type": ach.achievement_type,
            "required_value": ach.required_value,
            "current_progress": current_progress,
            "progress_percentage": progress_percentage,
            "is_earned": is_earned,
            "earned_at": earned_at,
            "reward": {
                "reward_type": ach.reward_type,
                "reward_name": ach.reward_name,
                "reward_points": ach.reward_points
            }
        }
    }
