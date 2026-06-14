from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from sqlalchemy.orm import aliased
import math
from typing import Optional
import uuid
from app import schemas, models, database, dependencies
from app.auth import verify_password, create_access_token
from datetime import timedelta, datetime, time, timezone

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Auth"])

@router.post("/auth/login", response_model=schemas.AdminLoginResponse)
async def admin_login(
    request: schemas.AdminLoginRequest,
    db: AsyncSession = Depends(database.get_db)
):
    query = select(models.Admin).filter(models.Admin.email == request.email)
    result = await db.execute(query)
    admin = result.scalars().first()
    
    if not admin or not verify_password(request.password, admin.password_hash):
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid credentials"})
        
    if not admin.status:
        return JSONResponse(status_code=401, content={"success": False, "message": "Account deactivated"})
        
    admin.last_login_at = func.now()
    await db.commit()
    
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(
        data={"sub": admin.admin_uuid, "role": admin.role}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "admin_uuid": admin.admin_uuid,
            "full_name": admin.full_name,
            "role": admin.role,
            "token": access_token
        }
    }

@router.get("/quizzes/pending", response_model=schemas.PendingQuizSubmissionsResponse)
async def get_pending_quizzes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query("pending"),
    category_id: Optional[int] = None,
    language_id: Optional[int] = None,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    base_query = (
        select(models.QuizSubmission, models.User, models.Category, models.Language)
        .outerjoin(models.User, models.QuizSubmission.user_id == models.User.id)
        .outerjoin(models.Category, models.QuizSubmission.category_id == models.Category.id)
        .outerjoin(models.Language, models.QuizSubmission.language_id == models.Language.id)
        .filter(models.QuizSubmission.review_status == status)
    )
    
    if category_id:
        base_query = base_query.filter(models.QuizSubmission.category_id == category_id)
    if language_id:
        base_query = base_query.filter(models.QuizSubmission.language_id == language_id)
        
    count_query = select(func.count()).select_from(base_query.subquery())
    total_records = (await db.execute(count_query)).scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    offset = (page - 1) * limit
    
    query = base_query.order_by(models.QuizSubmission.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for sub, user, cat, lang in rows:
        data.append({
            "submission_uuid": sub.submission_uuid,
            "question": sub.question,
            "category_name": cat.name if cat else "Unknown",
            "language_name": lang.name if lang else "Unknown",
            "submitted_by": {
                "user_uuid": user.uuid if user else "Unknown",
                "full_name": user.full_name if user else "Unknown User"
            },
            "review_status": sub.review_status,
            "submitted_at": sub.created_at
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

@router.post("/quizzes/review", response_model=schemas.ReviewQuizSubmissionResponse)
async def review_quiz_submission(
    request: schemas.ReviewQuizSubmissionRequest,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    if request.action not in ["approve", "reject"]:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid action. Must be 'approve' or 'reject'"})
        
    query = select(models.QuizSubmission).filter(models.QuizSubmission.submission_uuid == request.submission_uuid)
    result = await db.execute(query)
    submission = result.scalars().first()
    
    if not submission:
        return JSONResponse(status_code=404, content={"success": False, "message": "Submission Not Found"})
        
    submission.review_status = "approved" if request.action == "approve" else "rejected"
    submission.review_comment = request.review_comment
    submission.reviewed_by = current_admin.id
    submission.reviewed_at = func.now()
    
    if request.action == "approve":
        new_question = models.QuizQuestion(
            question_uuid=f"qst_{uuid.uuid4().hex}",
            category_id=submission.category_id,
            language_id=submission.language_id,
            bible_version_id=submission.bible_version_id,
            question=submission.question,
            answer_reason=submission.answer_explanation,
            bible_reference=submission.bible_reference,
            difficulty_level=submission.difficulty_level,
            status=True
        )
        db.add(new_question)
        await db.flush()
        
        options = [
            {"text": submission.option_a, "is_correct": submission.correct_option == "A"},
            {"text": submission.option_b, "is_correct": submission.correct_option == "B"},
            {"text": submission.option_c, "is_correct": submission.correct_option == "C"},
            {"text": submission.option_d, "is_correct": submission.correct_option == "D"},
        ]
        
        for opt in options:
            new_opt = models.QuizOption(
                question_id=new_question.id,
                option_text=opt["text"],
                is_correct=opt["is_correct"]
            )
            db.add(new_opt)
            
        noti = models.Notification(
            notification_uuid=f"noti_{uuid.uuid4().hex}",
            user_id=submission.user_id,
            title="Quiz Submission Approved",
            message=f"Your quiz question '{submission.question[:30]}...' has been approved!",
            notification_type="quiz_approved",
            is_read=False
        )
        db.add(noti)
        
    elif request.action == "reject":
        noti = models.Notification(
            notification_uuid=f"noti_{uuid.uuid4().hex}",
            user_id=submission.user_id,
            title="Quiz Submission Rejected",
            message=f"Your quiz question '{submission.question[:30]}...' was rejected. Reason: {request.review_comment}",
            notification_type="quiz_rejected",
            is_read=False
        )
        db.add(noti)
        
    await db.commit()
    
    return {
        "success": True,
        "message": f"Quiz {request.action}d successfully",
        "data": {
            "submission_uuid": submission.submission_uuid,
            "review_status": submission.review_status
        }
    }

@router.get("/translations/pending", response_model=schemas.PendingTranslationsResponse)
async def get_pending_translations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query("pending"),
    source_language_id: Optional[int] = None,
    target_language_id: Optional[int] = None,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    SourceLang = aliased(models.Language)
    TargetLang = aliased(models.Language)
    
    base_query = (
        select(
            models.QuizTranslation, 
            models.User, 
            models.QuizQuestion, 
            SourceLang, 
            TargetLang
        )
        .outerjoin(models.User, models.QuizTranslation.translator_user_id == models.User.id)
        .outerjoin(models.QuizQuestion, models.QuizTranslation.quiz_uuid == models.QuizQuestion.question_uuid)
        .outerjoin(SourceLang, models.QuizTranslation.source_language_id == SourceLang.id)
        .outerjoin(TargetLang, models.QuizTranslation.target_language_id == TargetLang.id)
        .filter(models.QuizTranslation.review_status == status)
    )
    
    if source_language_id:
        base_query = base_query.filter(models.QuizTranslation.source_language_id == source_language_id)
    if target_language_id:
        base_query = base_query.filter(models.QuizTranslation.target_language_id == target_language_id)
        
    count_query = select(func.count()).select_from(base_query.subquery())
    total_records = (await db.execute(count_query)).scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    offset = (page - 1) * limit
    
    query = base_query.order_by(models.QuizTranslation.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for trans, user, question, src_lang, tgt_lang in rows:
        data.append({
            "translation_uuid": trans.translation_uuid,
            "quiz_uuid": trans.quiz_uuid,
            "original_question": question.question if question else "Unknown Question",
            "translated_question": trans.translated_question,
            "source_language": src_lang.name if src_lang else "Unknown",
            "target_language": tgt_lang.name if tgt_lang else "Unknown",
            "submitted_by": {
                "user_uuid": user.uuid if user else "Unknown",
                "full_name": user.full_name if user else "Unknown User"
            },
            "review_status": trans.review_status,
            "submitted_at": trans.created_at
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

@router.post("/translations/review", response_model=schemas.ReviewTranslationResponse)
async def review_translation_submission(
    request: schemas.ReviewTranslationRequest,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    if request.action not in ["approve", "reject"]:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid action. Must be 'approve' or 'reject'"})
        
    query = select(models.QuizTranslation).filter(models.QuizTranslation.translation_uuid == request.translation_uuid)
    result = await db.execute(query)
    translation = result.scalars().first()
    
    if not translation:
        return JSONResponse(status_code=404, content={"success": False, "message": "Translation Not Found"})
        
    translation.review_status = "approved" if request.action == "approve" else "rejected"
    translation.review_comment = request.review_comment
    
    points_awarded = None
    
    if request.action == "approve":
        live_trans = models.LiveQuizTranslation(
            live_translation_uuid=f"lqtrans_{uuid.uuid4().hex}",
            quiz_uuid=translation.quiz_uuid,
            translator_user_id=translation.translator_user_id,
            target_language_id=translation.target_language_id,
            translated_question=translation.translated_question,
            translated_option_a=translation.translated_option_a,
            translated_option_b=translation.translated_option_b,
            translated_option_c=translation.translated_option_c,
            translated_option_d=translation.translated_option_d,
            translated_correct_option=translation.translated_correct_option,
            translated_answer_explanation=translation.translated_answer_explanation
        )
        db.add(live_trans)
        
        points_awarded = 25
        user_query = select(models.User).filter(models.User.id == translation.translator_user_id)
        user_result = await db.execute(user_query)
        translator = user_result.scalars().first()
        if translator:
            translator.total_points += points_awarded
            
        noti = models.Notification(
            notification_uuid=f"noti_{uuid.uuid4().hex}",
            user_id=translation.translator_user_id,
            title="Translation Approved",
            message=f"Your translation for quiz '{translation.quiz_uuid}' has been approved! You earned {points_awarded} points.",
            notification_type="translation_approved",
            is_read=False
        )
        db.add(noti)
        
    elif request.action == "reject":
        noti = models.Notification(
            notification_uuid=f"noti_{uuid.uuid4().hex}",
            user_id=translation.translator_user_id,
            title="Translation Rejected",
            message=f"Your translation for quiz '{translation.quiz_uuid}' was rejected. Reason: {request.review_comment}",
            notification_type="translation_rejected",
            is_read=False
        )
        db.add(noti)
        
    await db.commit()
    
    return {
        "success": True,
        "message": f"Translation {request.action}d successfully",
        "data": {
            "translation_uuid": translation.translation_uuid,
            "review_status": translation.review_status,
            "points_awarded": points_awarded
        }
    }

@router.get("/corrections/pending", response_model=schemas.PendingCorrectionsResponse)
async def get_pending_corrections(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    correction_type: Optional[str] = None,
    review_status: str = Query("pending"),
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    base_query = (
        select(
            models.QuizCorrection,
            models.User,
            models.QuizQuestion
        )
        .outerjoin(models.User, models.QuizCorrection.user_id == models.User.id)
        .outerjoin(models.QuizQuestion, models.QuizCorrection.quiz_uuid == models.QuizQuestion.question_uuid)
        .filter(models.QuizCorrection.review_status == review_status)
    )
    
    if correction_type:
        base_query = base_query.filter(models.QuizCorrection.correction_type == correction_type)
        
    count_query = select(func.count()).select_from(base_query.subquery())
    total_records = (await db.execute(count_query)).scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    offset = (page - 1) * limit
    
    query = base_query.order_by(models.QuizCorrection.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for corr, user, question in rows:
        data.append({
            "correction_uuid": corr.correction_uuid,
            "quiz_uuid": corr.quiz_uuid,
            "question": question.question if question else "Unknown Question",
            "correction_type": corr.correction_type,
            "current_value": corr.current_value,
            "suggested_value": corr.suggested_value,
            "user_comment": corr.user_comment,
            "submitted_by": {
                "user_uuid": user.uuid if user else "Unknown",
                "full_name": user.full_name if user else "Unknown User"
            },
            "review_status": corr.review_status,
            "submitted_at": corr.created_at
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

@router.post("/corrections/review", response_model=schemas.ReviewCorrectionResponse)
async def review_correction_submission(
    request: schemas.ReviewCorrectionRequest,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    if request.action not in ["approve", "reject"]:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid action. Must be 'approve' or 'reject'"})
        
    query = select(models.QuizCorrection).filter(models.QuizCorrection.correction_uuid == request.correction_uuid)
    result = await db.execute(query)
    correction = result.scalars().first()
    
    if not correction:
        return JSONResponse(status_code=404, content={"success": False, "message": "Correction Not Found"})
        
    correction.review_status = "approved" if request.action == "approve" else "rejected"
    correction.review_comment = request.review_comment
    
    points_awarded = None
    
    if request.action == "approve":
        question_query = select(models.QuizQuestion).filter(models.QuizQuestion.question_uuid == correction.quiz_uuid)
        q_result = await db.execute(question_query)
        quiz_question = q_result.scalars().first()
        
        if quiz_question:
            if correction.correction_type in ["wrong_question", "grammar_issue", "spelling_mistake", "translation_error"]:
                quiz_question.question = correction.suggested_value
            elif correction.correction_type == "wrong_explanation":
                quiz_question.answer_reason = correction.suggested_value
            elif correction.correction_type == "wrong_reference":
                quiz_question.bible_reference = correction.suggested_value
                
        points_awarded = 15
        user_query = select(models.User).filter(models.User.id == correction.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalars().first()
        if user:
            user.total_points += points_awarded
            
        noti = models.Notification(
            notification_uuid=f"noti_{uuid.uuid4().hex}",
            user_id=correction.user_id,
            title="Correction Approved",
            message=f"Your correction for quiz '{correction.quiz_uuid}' has been approved! You earned {points_awarded} points.",
            notification_type="correction_approved",
            is_read=False
        )
        db.add(noti)
        
    elif request.action == "reject":
        noti = models.Notification(
            notification_uuid=f"noti_{uuid.uuid4().hex}",
            user_id=correction.user_id,
            title="Correction Rejected",
            message=f"Your correction for quiz '{correction.quiz_uuid}' was rejected. Reason: {request.review_comment}",
            notification_type="correction_rejected",
            is_read=False
        )
        db.add(noti)
        
    await db.commit()
    
    return {
        "success": True,
        "message": f"Correction {request.action}d successfully",
        "data": {
            "correction_uuid": correction.correction_uuid,
            "review_status": correction.review_status,
            "points_awarded": points_awarded
        }
    }

@router.post("/achievements/create", response_model=schemas.CreateAchievementResponse)
async def create_achievement(
    request: schemas.CreateAchievementRequest,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    valid_types = ["quiz", "streak", "translation", "correction", "referral", "leaderboard", "reward"]
    if request.achievement_type not in valid_types:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Invalid achievement_type. Must be one of {valid_types}"})
        
    achievement = models.Achievement(
        achievement_uuid=f"ach_{uuid.uuid4().hex}",
        achievement_name=request.achievement_name,
        achievement_description=request.achievement_description,
        achievement_type=request.achievement_type,
        required_value=request.required_value,
        reward_points=request.reward_points,
        achievement_icon=request.achievement_icon,
        status=request.status,
        created_by=current_admin.id
    )
    
    db.add(achievement)
    await db.commit()
    
    return {
        "success": True,
        "message": "Achievement created successfully",
        "data": {
            "achievement_uuid": achievement.achievement_uuid
        }
    }

@router.get("/users", response_model=schemas.AdminUsersListResponse)
async def get_users_list(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    base_query = select(models.User)
    
    if status:
        base_query = base_query.filter(models.User.status == status)
        
    if search:
        search_filter = f"%{search}%"
        base_query = base_query.filter(
            or_(
                models.User.full_name.ilike(search_filter),
                models.User.email.ilike(search_filter),
                models.User.phone_number.ilike(search_filter)
            )
        )
        
    count_query = select(func.count()).select_from(base_query.subquery())
    total_records = (await db.execute(count_query)).scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    offset = (page - 1) * limit
    
    query = base_query.order_by(models.User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    data = []
    for user in users:
        data.append({
            "user_uuid": user.uuid,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "profile_image": user.profile_image,
            "status": user.status,
            "current_level": user.current_level,
            "total_points": user.total_points,
            "daily_streak": user.daily_streak,
            "created_at": user.created_at
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

@router.get("/users/{user_uuid}", response_model=schemas.AdminUserDetailResponse)
async def get_user_details(
    user_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    query = select(models.User).filter(models.User.uuid == user_uuid)
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        return JSONResponse(status_code=404, content={"success": False, "message": "User Not Found"})
        
    hist_query = select(
        func.count(models.QuizHistory.id).label("total_played"),
        func.sum(models.QuizHistory.correct_answers).label("total_correct"),
        func.sum(models.QuizHistory.total_questions).label("total_questions")
    ).filter(models.QuizHistory.user_id == user.id)
    hist_result = await db.execute(hist_query)
    hist_stats = hist_result.first()
    
    total_quizzes_played = hist_stats.total_played or 0
    total_correct = hist_stats.total_correct or 0
    total_questions = hist_stats.total_questions or 0
    accuracy_percentage = round((total_correct / total_questions) * 100, 1) if total_questions > 0 else 0.0
    
    ref_query = select(models.Referral).filter(models.Referral.user_id == user.id)
    ref_result = await db.execute(ref_query)
    referral = ref_result.scalars().first()
    total_referrals = referral.total_referrals if referral else 0
    
    rew_query = select(func.count(models.RewardClaim.id)).filter(models.RewardClaim.user_id == user.id)
    total_rewards_claimed = (await db.execute(rew_query)).scalar() or 0
    
    ach_query = select(func.count(models.UserAchievement.id)).filter(models.UserAchievement.user_id == user.id)
    total_achievements = (await db.execute(ach_query)).scalar() or 0
    
    q_query = select(func.count(models.QuizSubmission.id)).filter(models.QuizSubmission.user_id == user.id)
    total_created_quizzes = (await db.execute(q_query)).scalar() or 0
    
    t_query = select(func.count(models.QuizTranslation.id)).filter(models.QuizTranslation.translator_user_id == user.id)
    total_translations = (await db.execute(t_query)).scalar() or 0
    
    c_query = select(func.count(models.QuizCorrection.id)).filter(models.QuizCorrection.user_id == user.id)
    total_corrections = (await db.execute(c_query)).scalar() or 0
    
    return {
        "success": True,
        "data": {
            "user_uuid": user.uuid,
            "full_name": user.full_name or "Unknown",
            "email": user.email,
            "phone_number": user.phone_number or "Unknown",
            "country_code": user.country_code or "Unknown",
            "profile_image": user.profile_image,
            "status": user.status,
            "current_level": user.current_level,
            "total_points": user.total_points,
            "daily_streak": user.daily_streak,
            "total_quizzes_played": total_quizzes_played,
            "accuracy_percentage": accuracy_percentage,
            "total_referrals": total_referrals,
            "total_rewards_claimed": total_rewards_claimed,
            "total_achievements": total_achievements,
            "total_created_quizzes": total_created_quizzes,
            "total_translations": total_translations,
            "total_corrections": total_corrections,
            "member_since": user.created_at,
            "last_login_at": user.last_login_at
        }
    }

@router.get("/dashboard", response_model=schemas.AdminDashboardResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    today_start = datetime.combine(datetime.utcnow().date(), time.min).replace(tzinfo=timezone.utc)
    
    total_users = (await db.execute(select(func.count(models.User.id)))).scalar() or 0
    active_users = (await db.execute(select(func.count(models.User.id)).filter(models.User.status == "active"))).scalar() or 0
    blocked_users = (await db.execute(select(func.count(models.User.id)).filter(models.User.status == "blocked"))).scalar() or 0
    today_new_users = (await db.execute(select(func.count(models.User.id)).filter(models.User.created_at >= today_start))).scalar() or 0
    
    total_quizzes = (await db.execute(select(func.count(models.QuizQuestion.id)))).scalar() or 0
    pending_quiz_reviews = (await db.execute(select(func.count(models.QuizSubmission.id)).filter(models.QuizSubmission.review_status == "pending"))).scalar() or 0
    
    pending_translations = (await db.execute(select(func.count(models.QuizTranslation.id)).filter(models.QuizTranslation.review_status == "pending"))).scalar() or 0
    pending_corrections = (await db.execute(select(func.count(models.QuizCorrection.id)).filter(models.QuizCorrection.review_status == "pending"))).scalar() or 0
    
    total_groups = (await db.execute(select(func.count(models.Group.id)))).scalar() or 0
    
    total_rewards_claimed = (await db.execute(select(func.count(models.RewardClaim.id)))).scalar() or 0
    
    today_quizzes_played = (await db.execute(select(func.count(models.QuizHistory.id)).filter(models.QuizHistory.created_at >= today_start))).scalar() or 0
    today_points_earned = (await db.execute(select(func.sum(models.QuizHistory.points_earned)).filter(models.QuizHistory.created_at >= today_start))).scalar() or 0
    
    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "total_quizzes": total_quizzes,
            "pending_quiz_reviews": pending_quiz_reviews,
            "pending_translations": pending_translations,
            "pending_corrections": pending_corrections,
            "total_groups": total_groups,
            "total_rewards_claimed": total_rewards_claimed,
            "today_new_users": today_new_users,
            "today_quizzes_played": today_quizzes_played,
            "today_points_earned": today_points_earned
        }
    }

@router.get("/analytics", response_model=schemas.AdminAnalyticsResponse)
async def get_admin_analytics(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    analytics_type: str = Query("all"),
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    valid_types = ["users", "quizzes", "languages", "groups", "rewards", "all"]
    if analytics_type not in valid_types:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Invalid analytics_type. Must be one of {valid_types}"})
        
    data = schemas.AdminAnalyticsData()
    
    if analytics_type in ["users", "all"]:
        q_ug = select(
            func.date(models.User.created_at).label("d"), 
            func.count(models.User.id)
        ).group_by("d").order_by("d")
        if from_date:
            q_ug = q_ug.filter(models.User.created_at >= from_date)
        if to_date:
            q_ug = q_ug.filter(models.User.created_at <= to_date)
            
        res_ug = await db.execute(q_ug)
        user_growth = []
        for r in res_ug.all():
            if r[0]:
                user_growth.append({"date": str(r[0]), "count": r[1]})
        data.user_growth = user_growth
        
        q_dau = select(
            func.date(models.User.last_login_at).label("d"), 
            func.count(models.User.id)
        ).filter(models.User.last_login_at != None).group_by("d").order_by("d")
        if from_date:
            q_dau = q_dau.filter(models.User.last_login_at >= from_date)
        if to_date:
            q_dau = q_dau.filter(models.User.last_login_at <= to_date)
            
        res_dau = await db.execute(q_dau)
        daily_active_users = []
        for r in res_dau.all():
            if r[0]:
                daily_active_users.append({"date": str(r[0]), "count": r[1]})
        data.daily_active_users = daily_active_users
        
    if analytics_type in ["quizzes", "all"]:
        q_qc = select(
            func.date(models.QuizHistory.created_at).label("d"), 
            func.count(models.QuizHistory.id)
        ).group_by("d").order_by("d")
        if from_date:
            q_qc = q_qc.filter(models.QuizHistory.created_at >= from_date)
        if to_date:
            q_qc = q_qc.filter(models.QuizHistory.created_at <= to_date)
            
        res_qc = await db.execute(q_qc)
        quiz_completion = []
        for r in res_qc.all():
            if r[0]:
                quiz_completion.append({"date": str(r[0]), "completed_quizzes": r[1]})
        data.quiz_completion = quiz_completion
        
    if analytics_type in ["languages", "all"]:
        q_lu = select(
            models.Language.name,
            func.count(models.User.id)
        ).outerjoin(models.User, models.User.primary_language == models.Language.code).group_by(models.Language.name)
        
        res_lu = await db.execute(q_lu)
        language_usage = []
        for r in res_lu.all():
            if r[0]:
                language_usage.append({"language": r[0], "users": r[1] or 0})
        data.language_usage = language_usage
        
    return {
        "success": True,
        "data": data
    }

@router.get("/settings", response_model=schemas.AdminSettingsResponse)
async def get_system_settings(
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    query = select(models.SystemSetting)
    result = await db.execute(query)
    settings = result.scalars().all()
    
    settings_map = {
        "quiz_points_per_correct_answer": 10,
        "translation_reward_points": 25,
        "correction_reward_points": 15,
        "referral_reward_points": 50,
        "max_group_members": 100,
        "daily_streak_bonus": 20,
        "notification_enabled": True,
        "achievement_enabled": True
    }
    
    for s in settings:
        if s.setting_key in settings_map:
            settings_map[s.setting_key] = s.setting_value
            
    return {
        "success": True,
        "data": settings_map
    }

@router.put("/settings", response_model=schemas.UpdateAdminSettingsResponse)
async def update_system_settings(
    request: schemas.UpdateAdminSettingsRequest,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    update_data = request.model_dump(exclude_unset=True)
    
    if not update_data:
        return JSONResponse(status_code=400, content={"success": False, "message": "No settings provided for update"})
        
    updated_at = datetime.now(timezone.utc)
    
    for key, value in update_data.items():
        q = select(models.SystemSetting).filter(models.SystemSetting.setting_key == key)
        res = await db.execute(q)
        setting = res.scalars().first()
        
        if setting:
            setting.setting_value = value
            setting.updated_by = current_admin.id
            setting.updated_at = updated_at
        else:
            new_setting = models.SystemSetting(
                setting_key=key,
                setting_value=value,
                updated_by=current_admin.id,
                updated_at=updated_at
            )
            db.add(new_setting)
            
    audit_log = models.AdminAuditLog(
        audit_uuid=f"audit_{uuid.uuid4().hex}",
        admin_id=current_admin.id,
        action_type="settings_updated",
        entity_type="system_settings",
        new_value=update_data,
        created_at=updated_at
    )
    db.add(audit_log)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "System settings updated successfully",
        "updated_by": current_admin.admin_uuid,
        "updated_at": updated_at
    }

@router.get("/audit-logs", response_model=schemas.AdminAuditLogsResponse)
async def get_admin_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin_uuid: Optional[str] = None,
    action_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    base_query = select(models.AdminAuditLog, models.Admin).join(models.Admin)
    
    if admin_uuid:
        base_query = base_query.filter(models.Admin.admin_uuid == admin_uuid)
    if action_type:
        base_query = base_query.filter(models.AdminAuditLog.action_type == action_type)
    if from_date:
        base_query = base_query.filter(models.AdminAuditLog.created_at >= from_date)
    if to_date:
        base_query = base_query.filter(models.AdminAuditLog.created_at <= to_date)
        
    count_query = select(func.count()).select_from(base_query.subquery())
    total_records = (await db.execute(count_query)).scalar() or 0
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    offset = (page - 1) * limit
    
    query = base_query.order_by(models.AdminAuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    
    data = []
    for audit, admin in result.all():
        data.append({
            "audit_uuid": audit.audit_uuid,
            "admin_uuid": admin.admin_uuid,
            "admin_name": admin.full_name,
            "action_type": audit.action_type,
            "entity_type": audit.entity_type,
            "entity_uuid": audit.entity_uuid,
            "ip_address": audit.ip_address,
            "created_at": audit.created_at
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

@router.get("/audit-logs/{audit_uuid}", response_model=schemas.AdminAuditLogDetailResponse)
async def get_admin_audit_log_details(
    audit_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_admin: models.Admin = Depends(dependencies.get_current_admin)
):
    query = select(models.AdminAuditLog, models.Admin).join(models.Admin).filter(models.AdminAuditLog.audit_uuid == audit_uuid)
    result = await db.execute(query)
    record = result.first()
    
    if not record:
        return JSONResponse(status_code=404, content={"success": False, "message": "Audit Log Not Found"})
        
    audit, admin = record
    
    return {
        "success": True,
        "data": {
            "audit_uuid": audit.audit_uuid,
            "admin_uuid": admin.admin_uuid,
            "admin_name": admin.full_name,
            "action_type": audit.action_type,
            "entity_type": audit.entity_type,
            "entity_uuid": audit.entity_uuid,
            "old_value": audit.old_value,
            "new_value": audit.new_value,
            "ip_address": audit.ip_address,
            "user_agent": audit.user_agent,
            "created_at": audit.created_at
        }
    }
