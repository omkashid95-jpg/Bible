from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import uuid
from typing import Optional
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/create-quiz", tags=["Create Quiz"])

@router.get("/master-data", response_model=schemas.MasterDataResponse)
async def get_master_data(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Fetch categories
    categories_result = await db.execute(select(models.Category).filter(models.Category.status == True))
    categories = categories_result.scalars().all()
    
    # Fetch languages
    languages_result = await db.execute(select(models.Language))
    languages = languages_result.scalars().all()
    
    # Fetch bible versions
    bible_versions_result = await db.execute(select(models.BibleVersion))
    bible_versions = bible_versions_result.scalars().all()
    
    # Fetch age groups
    age_groups_result = await db.execute(select(models.AgeGroup))
    age_groups = age_groups_result.scalars().all()
    
    # Fetch difficulty levels
    difficulty_levels_result = await db.execute(select(models.DifficultyLevel))
    difficulty_levels = difficulty_levels_result.scalars().all()
    
    return {
        "success": True,
        "data": {
            "categories": [{"id": c.id, "name": c.name} for c in categories],
            "languages": [{"id": l.id, "name": l.name, "code": l.code} for l in languages],
            "bible_versions": [{"id": b.id, "name": b.name, "short_name": b.short_name} for b in bible_versions],
            "age_groups": [{"id": a.id, "name": a.name} for a in age_groups],
            "difficulty_levels": [{"id": d.id, "name": d.name} for d in difficulty_levels]
        }
    }

@router.post("/check-duplicate", response_model=schemas.CheckDuplicateResponse)
async def check_duplicate(
    request: schemas.CheckDuplicateRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Search existing questions doing case-insensitive text match
    query = select(models.QuizQuestion).filter(
        func.lower(models.QuizQuestion.question) == request.question.strip().lower(),
        models.QuizQuestion.language_id == request.language_id,
        models.QuizQuestion.bible_version_id == request.bible_version_id
    )
    result = await db.execute(query)
    existing_question = result.scalars().first()
    
    if existing_question:
        return {
            "success": True,
            "is_duplicate": True,
            "message": "Similar question already exists",
            "existing_question_id": existing_question.id
        }
        
    return {
        "success": True,
        "is_duplicate": False,
        "message": "Question can be submitted"
    }

@router.post("/submit", response_model=schemas.CreateQuizSubmitResponse)
async def submit_quiz(
    request: schemas.CreateQuizSubmitRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate category
    cat_result = await db.execute(select(models.Category).filter(models.Category.id == request.category_id))
    if not cat_result.scalars().first():
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid category"})

    # Validate language
    lang_result = await db.execute(select(models.Language).filter(models.Language.id == request.language_id))
    if not lang_result.scalars().first():
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid language"})

    # Validate bible version
    bv_result = await db.execute(select(models.BibleVersion).filter(models.BibleVersion.id == request.bible_version_id))
    if not bv_result.scalars().first():
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid bible version"})
        
    # Check duplicate
    dup_query = select(models.QuizQuestion).filter(
        func.lower(models.QuizQuestion.question) == request.question.strip().lower(),
        models.QuizQuestion.language_id == request.language_id,
        models.QuizQuestion.bible_version_id == request.bible_version_id
    )
    dup_result = await db.execute(dup_query)
    if dup_result.scalars().first():
        return JSONResponse(status_code=409, content={"success": False, "message": "Duplicate question detected"})

    # Save submission
    submission_uuid = f"sub_{uuid.uuid4().hex}"
    new_submission = models.QuizSubmission(
        submission_uuid=submission_uuid,
        user_id=current_user.id,
        category_id=request.category_id,
        language_id=request.language_id,
        bible_version_id=request.bible_version_id,
        question=request.question,
        option_a=request.option_a,
        option_b=request.option_b,
        option_c=request.option_c,
        option_d=request.option_d,
        correct_option=request.correct_option,
        answer_explanation=request.answer_explanation,
        bible_reference=request.bible_reference,
        difficulty_level=request.difficulty_level,
        age_group_id=request.age_group_id,
        review_status="pending"
    )
    db.add(new_submission)
    await db.commit()

    return {
        "success": True,
        "message": "Quiz submitted successfully",
        "submission_uuid": submission_uuid,
        "review_status": "pending"
    }

@router.get("/my-submissions", response_model=schemas.MySubmissionsResponse)
async def get_my_submissions(
    page: int = 1,
    limit: int = 10,
    review_status: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.QuizSubmission).filter(models.QuizSubmission.user_id == current_user.id)
    
    if review_status and review_status in ["pending", "approved", "rejected"]:
        query = query.filter(models.QuizSubmission.review_status == review_status)
        
    # Get total records for pagination
    total_records_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_records = total_records_result.scalar() or 0
    
    import math
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    # Apply pagination and sorting
    offset = (page - 1) * limit
    paginated_query = query.order_by(models.QuizSubmission.created_at.desc()).offset(offset).limit(limit)
    
    submissions_result = await db.execute(paginated_query)
    submissions = submissions_result.scalars().all()
    
    # Fast map loading for names rather than deep SQL joins
    cat_result = await db.execute(select(models.Category))
    categories_map = {c.id: c.name for c in cat_result.scalars().all()}
    
    lang_result = await db.execute(select(models.Language))
    languages_map = {l.id: l.name for l in lang_result.scalars().all()}
    
    data = []
    for sub in submissions:
        data.append({
            "submission_uuid": sub.submission_uuid,
            "question": sub.question,
            "category_name": categories_map.get(sub.category_id, "Unknown"),
            "language": languages_map.get(sub.language_id, "Unknown"),
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

@router.get("/submission/{submission_uuid}", response_model=schemas.SubmissionDetailsResponse)
async def get_submission_details(
    submission_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Fetch submission securely bound to logged in user
    sub_result = await db.execute(select(models.QuizSubmission).filter(
        models.QuizSubmission.submission_uuid == submission_uuid,
        models.QuizSubmission.user_id == current_user.id
    ))
    submission = sub_result.scalars().first()
    
    if not submission:
        return JSONResponse(status_code=404, content={"success": False, "message": "Submission not found"})
        
    # Fetch mapping data explicitly
    cat_result = await db.execute(select(models.Category).filter(models.Category.id == submission.category_id))
    category = cat_result.scalars().first()
    
    lang_result = await db.execute(select(models.Language).filter(models.Language.id == submission.language_id))
    language = lang_result.scalars().first()
    
    bv_result = await db.execute(select(models.BibleVersion).filter(models.BibleVersion.id == submission.bible_version_id))
    bible_version = bv_result.scalars().first()
    
    return {
        "success": True,
        "data": {
            "submission_uuid": submission.submission_uuid,
            "category_id": submission.category_id,
            "category_name": category.name if category else "Unknown",
            "language_id": submission.language_id,
            "language_name": language.name if language else "Unknown",
            "bible_version_id": submission.bible_version_id,
            "bible_version_name": bible_version.short_name if bible_version else "Unknown",
            "question": submission.question,
            "option_a": submission.option_a,
            "option_b": submission.option_b,
            "option_c": submission.option_c,
            "option_d": submission.option_d,
            "correct_option": submission.correct_option,
            "answer_explanation": submission.answer_explanation,
            "bible_reference": submission.bible_reference,
            "difficulty_level": submission.difficulty_level,
            "review_status": submission.review_status,
            "review_comment": submission.review_comment,
            "submitted_at": submission.created_at
        }
    }
