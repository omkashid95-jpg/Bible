from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid
from app import schemas, models, database, dependencies
import math

router = APIRouter(prefix="/api/v1/correction-quiz", tags=["Correction Quiz"])

@router.get("/available-quizzes", response_model=schemas.AvailableCorrectionsResponse)
async def get_available_quizzes(
    page: int = 1,
    limit: int = 10,
    category_id: Optional[int] = None,
    language_id: Optional[int] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.QuizQuestion).filter(models.QuizQuestion.status == True)
    
    if category_id:
        query = query.filter(models.QuizQuestion.category_id == category_id)
        
    if language_id:
        query = query.filter(models.QuizQuestion.language_id == language_id)

    total_records_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_records = total_records_result.scalar() or 0
    
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    paginated_query = query.order_by(models.QuizQuestion.created_at.desc()).offset(offset).limit(limit)
    
    questions_result = await db.execute(paginated_query)
    questions = questions_result.scalars().all()
    
    cat_result = await db.execute(select(models.Category))
    categories_map = {c.id: c.name for c in cat_result.scalars().all()}
    
    lang_result = await db.execute(select(models.Language))
    languages_map = {l.id: l.name for l in lang_result.scalars().all()}
    
    bv_result = await db.execute(select(models.BibleVersion))
    bv_map = {b.id: b.short_name for b in bv_result.scalars().all()}
    
    data = []
    for q in questions:
        data.append({
            "quiz_uuid": q.question_uuid,
            "question": q.question,
            "language": languages_map.get(q.language_id, "Unknown"),
            "category_name": categories_map.get(q.category_id, "Unknown"),
            "bible_version": bv_map.get(q.bible_version_id, "Unknown"),
            "created_at": q.created_at
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

@router.get("/details/{quiz_uuid}", response_model=schemas.CorrectionQuizDetailsResponse)
async def get_correction_quiz_details(
    quiz_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.QuizQuestion).filter(
        models.QuizQuestion.question_uuid == quiz_uuid,
        models.QuizQuestion.status == True
    ).options(selectinload(models.QuizQuestion.options))
    
    result = await db.execute(query)
    question = result.scalars().first()
    
    if not question:
        return JSONResponse(status_code=404, content={"success": False, "message": "Quiz not found"})
        
    # Maps
    cat_result = await db.execute(select(models.Category).filter(models.Category.id == question.category_id))
    category = cat_result.scalars().first()
    
    lang_result = await db.execute(select(models.Language).filter(models.Language.id == question.language_id))
    language = lang_result.scalars().first()
    
    bv_result = await db.execute(select(models.BibleVersion).filter(models.BibleVersion.id == question.bible_version_id))
    bible_version = bv_result.scalars().first()
    
    options = question.options
    option_map = {}
    correct_option = ""
    
    letters = ["A", "B", "C", "D"]
    for i, opt in enumerate(options[:4]):
        letter = letters[i]
        option_map[f"option_{letter.lower()}"] = opt.option_text
        if opt.is_correct:
            correct_option = letter

    return {
        "success": True,
        "data": {
            "quiz_uuid": question.question_uuid,
            "question": question.question,
            "option_a": option_map.get("option_a", ""),
            "option_b": option_map.get("option_b", ""),
            "option_c": option_map.get("option_c", ""),
            "option_d": option_map.get("option_d", ""),
            "correct_option": correct_option,
            "answer_explanation": question.answer_reason or "",
            "bible_reference": question.bible_reference or "",
            "language": language.name if language else "Unknown",
            "category_name": category.name if category else "Unknown",
            "bible_version": bible_version.short_name if bible_version else "Unknown"
        }
    }

@router.post("/submit", response_model=schemas.SubmitCorrectionResponse)
async def submit_correction(
    request: schemas.SubmitCorrectionRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    valid_types = [
        "wrong_question", "wrong_answer", "wrong_bible_reference",
        "spelling_mistake", "grammar_mistake", "wrong_explanation", "wrong_translation"
    ]
    if request.correction_type not in valid_types:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid correction type"})

    # Validate quiz exists
    quiz_query = select(models.QuizQuestion).filter(models.QuizQuestion.question_uuid == request.quiz_uuid)
    quiz_result = await db.execute(quiz_query)
    quiz = quiz_result.scalars().first()
    if not quiz:
        return JSONResponse(status_code=400, content={"success": False, "message": "Quiz not found"})

    # Check for duplicate pending correction from this user
    dup_query = select(models.QuizCorrection).filter(
        models.QuizCorrection.quiz_uuid == request.quiz_uuid,
        models.QuizCorrection.user_id == current_user.id,
        models.QuizCorrection.correction_type == request.correction_type,
        models.QuizCorrection.review_status == "pending"
    )
    dup_result = await db.execute(dup_query)
    if dup_result.scalars().first():
        return JSONResponse(status_code=409, content={"success": False, "message": "Duplicate correction already exists"})

    # Save correction
    correction_uuid = f"corr_{uuid.uuid4().hex}"
    new_correction = models.QuizCorrection(
        correction_uuid=correction_uuid,
        quiz_uuid=request.quiz_uuid,
        user_id=current_user.id,
        correction_type=request.correction_type,
        current_value=request.current_value,
        suggested_value=request.suggested_value,
        user_comment=request.user_comment,
        review_status="pending"
    )
    db.add(new_correction)
    await db.commit()

    return {
        "success": True,
        "message": "Correction submitted successfully",
        "correction_uuid": correction_uuid,
        "review_status": "pending"
    }

@router.get("/my-corrections", response_model=schemas.MyCorrectionsResponse)
async def get_my_corrections(
    page: int = 1,
    limit: int = 10,
    review_status: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.QuizCorrection).filter(models.QuizCorrection.user_id == current_user.id)
    
    if review_status and review_status in ["pending", "approved", "rejected"]:
        query = query.filter(models.QuizCorrection.review_status == review_status)
        
    total_records_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_records = total_records_result.scalar() or 0
    
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    paginated_query = query.order_by(models.QuizCorrection.created_at.desc()).offset(offset).limit(limit)
    
    corrections_result = await db.execute(paginated_query)
    corrections = corrections_result.scalars().all()
    
    data = []
    for c in corrections:
        data.append({
            "correction_uuid": c.correction_uuid,
            "quiz_uuid": c.quiz_uuid,
            "correction_type": c.correction_type,
            "review_status": c.review_status,
            "review_comment": c.review_comment,
            "submitted_at": c.created_at
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
