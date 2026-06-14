from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import math
from datetime import date
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/leaderboard", tags=["Leaderboard"])

@router.get("/global", response_model=schemas.GlobalLeaderboardResponse)
async def get_global_leaderboard(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Get total counts
    count_query = select(func.count()).select_from(models.LeaderboardRanking)
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    # Pagination
    offset = (page - 1) * limit
    
    # Fetch paginated leaderboard by joining with Users table
    query = (
        select(models.LeaderboardRanking, models.User)
        .join(models.User, models.LeaderboardRanking.user_id == models.User.id)
        .order_by(models.LeaderboardRanking.rank.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for rank_record, user_record in rows:
        data.append({
            "rank": rank_record.rank,
            "user_uuid": user_record.user_uuid,
            "full_name": user_record.full_name,
            "profile_image": user_record.profile_image,
            "total_points": rank_record.total_points,
            "current_level": rank_record.current_level,
            "daily_streak": rank_record.daily_streak
        })
        
    # Isolate Current User's Ranking
    cu_query = select(models.LeaderboardRanking).filter(models.LeaderboardRanking.user_id == current_user.id)
    cu_result = await db.execute(cu_query)
    cu_rank = cu_result.scalars().first()
    
    current_user_data = {
        "rank": cu_rank.rank if cu_rank else 0,
        "total_points": cu_rank.total_points if cu_rank else 0,
        "current_level": cu_rank.current_level if cu_rank else 1
    }

    return {
        "success": True,
        "data": data,
        "current_user": current_user_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@router.get("/daily", response_model=schemas.DailyLeaderboardResponse)
async def get_daily_leaderboard(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    today = date.today()
    
    # Get total counts for today
    count_query = select(func.count()).select_from(models.DailyLeaderboard).filter(models.DailyLeaderboard.leaderboard_date == today)
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    # Pagination
    offset = (page - 1) * limit
    
    # Fetch paginated leaderboard by joining with Users table
    query = (
        select(models.DailyLeaderboard, models.User)
        .join(models.User, models.DailyLeaderboard.user_id == models.User.id)
        .filter(models.DailyLeaderboard.leaderboard_date == today)
        .order_by(models.DailyLeaderboard.rank.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for dl_record, user_record in rows:
        data.append({
            "rank": dl_record.rank,
            "user_uuid": user_record.user_uuid,
            "full_name": user_record.full_name,
            "profile_image": user_record.profile_image,
            "points_today": dl_record.points_today,
            "quizzes_completed_today": dl_record.quizzes_completed_today,
            "accuracy_percentage": dl_record.accuracy_percentage
        })
        
    # Isolate Current User's Ranking for today
    cu_query = select(models.DailyLeaderboard).filter(
        models.DailyLeaderboard.user_id == current_user.id,
        models.DailyLeaderboard.leaderboard_date == today
    )
    cu_result = await db.execute(cu_query)
    cu_rank = cu_result.scalars().first()
    
    current_user_data = {
        "rank": cu_rank.rank if cu_rank else 0,
        "points_today": cu_rank.points_today if cu_rank else 0,
        "quizzes_completed_today": cu_rank.quizzes_completed_today if cu_rank else 0
    }

    return {
        "success": True,
        "data": data,
        "current_user": current_user_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@router.get("/language", response_model=schemas.LanguageLeaderboardResponse)
async def get_language_leaderboard(
    language_id: int,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    lang_query = select(models.Language).filter(models.Language.id == language_id)
    lang_result = await db.execute(lang_query)
    language = lang_result.scalars().first()
    
    if not language:
        return JSONResponse(status_code=400, content={"success": False, "message": "Language not found"})
        
    base_query = (
        select(models.LeaderboardRanking)
        .join(models.UserLanguage, models.LeaderboardRanking.user_id == models.UserLanguage.user_id)
        .filter(models.UserLanguage.language_name == language.name)
    )
    
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    
    query = (
        select(models.LeaderboardRanking, models.User)
        .join(models.User, models.LeaderboardRanking.user_id == models.User.id)
        .join(models.UserLanguage, models.LeaderboardRanking.user_id == models.UserLanguage.user_id)
        .filter(models.UserLanguage.language_name == language.name)
        .order_by(models.LeaderboardRanking.total_points.desc())
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    current_rank = offset + 1
    for rank_record, user_record in rows:
        data.append({
            "rank": current_rank,
            "user_uuid": user_record.user_uuid,
            "full_name": user_record.full_name,
            "profile_image": user_record.profile_image,
            "total_points": rank_record.total_points,
            "current_level": rank_record.current_level,
            "daily_streak": rank_record.daily_streak
        })
        current_rank += 1
        
    cu_lang_query = select(models.UserLanguage).filter(
        models.UserLanguage.user_id == current_user.id,
        models.UserLanguage.language_name == language.name
    )
    cu_lang_result = await db.execute(cu_lang_query)
    if not cu_lang_result.scalars().first():
        current_user_data = {
            "rank": 0,
            "total_points": 0,
            "current_level": 0
        }
    else:
        cu_rank_query = select(models.LeaderboardRanking).filter(models.LeaderboardRanking.user_id == current_user.id)
        cu_rank_result = await db.execute(cu_rank_query)
        cu_ranking = cu_rank_result.scalars().first()
        
        if cu_ranking:
            higher_points_query = select(func.count()).select_from(
                select(models.LeaderboardRanking)
                .join(models.UserLanguage, models.LeaderboardRanking.user_id == models.UserLanguage.user_id)
                .filter(models.UserLanguage.language_name == language.name)
                .filter(models.LeaderboardRanking.total_points > cu_ranking.total_points)
                .subquery()
            )
            higher_points_result = await db.execute(higher_points_query)
            higher_count = higher_points_result.scalar() or 0
            
            current_user_data = {
                "rank": higher_count + 1,
                "total_points": cu_ranking.total_points,
                "current_level": cu_ranking.current_level
            }
        else:
            current_user_data = {
                "rank": 0,
                "total_points": 0,
                "current_level": 1
            }

    return {
        "success": True,
        "selected_language": {
            "id": language.id,
            "name": language.name
        },
        "data": data,
        "current_user": current_user_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@router.get("/my-rank", response_model=schemas.MyRankResponse)
async def get_my_rank(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    today = date.today()

    user_uuid = current_user.uuid
    full_name = current_user.full_name or ""
    profile_image = current_user.profile_image

    gr_query = select(models.LeaderboardRanking).filter(models.LeaderboardRanking.user_id == current_user.id)
    gr_result = await db.execute(gr_query)
    global_ranking = gr_result.scalars().first()

    global_rank = global_ranking.rank if global_ranking else 0
    total_points = global_ranking.total_points if global_ranking else current_user.total_points
    current_level = global_ranking.current_level if global_ranking else current_user.current_level
    daily_streak = global_ranking.daily_streak if global_ranking else current_user.daily_streak

    dr_query = select(models.DailyLeaderboard).filter(
        models.DailyLeaderboard.user_id == current_user.id,
        models.DailyLeaderboard.leaderboard_date == today
    )
    dr_result = await db.execute(dr_query)
    daily_ranking = dr_result.scalars().first()
    daily_rank = daily_ranking.rank if daily_ranking else 0

    ul_query = select(models.UserLanguage).filter(
        models.UserLanguage.user_id == current_user.id,
        models.UserLanguage.is_primary == True
    )
    ul_result = await db.execute(ul_query)
    primary_lang = ul_result.scalars().first()
    
    language_rank = 0
    if primary_lang and global_ranking:
        lr_query = select(func.count()).select_from(
            select(models.LeaderboardRanking)
            .join(models.UserLanguage, models.LeaderboardRanking.user_id == models.UserLanguage.user_id)
            .filter(models.UserLanguage.language_name == primary_lang.language_name)
            .filter(models.LeaderboardRanking.total_points > global_ranking.total_points)
            .subquery()
        )
        lr_result = await db.execute(lr_query)
        language_rank = (lr_result.scalar() or 0) + 1
    elif global_ranking:
        language_rank = global_rank

    qh_query = select(
        func.count(models.QuizHistory.id).label("total_quizzes"),
        func.sum(models.QuizHistory.correct_answers).label("total_correct"),
        func.sum(models.QuizHistory.total_questions).label("total_questions")
    ).filter(models.QuizHistory.user_id == current_user.id)
    qh_result = await db.execute(qh_query)
    stats = qh_result.first()

    total_quizzes_played = stats.total_quizzes or 0
    total_correct_answers = stats.total_correct or 0
    total_questions = stats.total_questions or 0
    
    accuracy_percentage = 0.0
    if total_questions > 0:
        accuracy_percentage = round((total_correct_answers / total_questions) * 100, 2)

    return {
        "success": True,
        "data": {
            "user_uuid": user_uuid,
            "full_name": full_name,
            "profile_image": profile_image,
            "global_rank": global_rank,
            "daily_rank": daily_rank,
            "language_rank": language_rank,
            "total_points": total_points,
            "current_level": current_level,
            "daily_streak": daily_streak,
            "total_quizzes_played": total_quizzes_played,
            "total_correct_answers": total_correct_answers,
            "accuracy_percentage": accuracy_percentage
        }
    }
