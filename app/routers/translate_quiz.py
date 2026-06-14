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

router = APIRouter(prefix="/api/v1/translate-quiz", tags=["Translate Quiz"])

@router.get("/available-quizzes", response_model=schemas.AvailableTranslationsResponse)
async def get_available_quizzes(
    page: int = 1,
    limit: int = 10,
    source_language_id: Optional[int] = None,
    target_language_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.QuizQuestion).filter(models.QuizQuestion.status == True)
    
    if source_language_id:
        query = query.filter(models.QuizQuestion.language_id == source_language_id)
        
    if category_id:
        query = query.filter(models.QuizQuestion.category_id == category_id)

    total_records_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_records = total_records_result.scalar() or 0
    
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    paginated_query = query.order_by(models.QuizQuestion.created_at.desc()).offset(offset).limit(limit)
    
    questions_result = await db.execute(paginated_query)
    questions = questions_result.scalars().all()
    
    # Fast Map Lookups
    cat_result = await db.execute(select(models.Category))
    categories_map = {c.id: c.name for c in cat_result.scalars().all()}
    
    lang_result = await db.execute(select(models.Language))
    languages_map = {l.id: l.name for l in lang_result.scalars().all()}
    
    bv_result = await db.execute(select(models.BibleVersion))
    bv_map = {b.id: b.short_name for b in bv_result.scalars().all()}
    
    target_language_name = languages_map.get(target_language_id, "Unknown") if target_language_id else "Any"
    
    data = []
    for q in questions:
        data.append({
            "quiz_uuid": q.question_uuid,
            "question": q.question,
            "source_language": languages_map.get(q.language_id, "Unknown"),
            "target_language": target_language_name,
            "category_name": categories_map.get(q.category_id, "Unknown"),
            "bible_version": bv_map.get(q.bible_version_id, "Unknown"),
            "created_by": "Admin",
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

@router.get("/details/{quiz_uuid}", response_model=schemas.TranslationQuizDetailsResponse)
async def get_translation_quiz_details(
    quiz_uuid: str,
    target_language_id: Optional[int] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Fetch original quiz with options
    query = select(models.QuizQuestion).filter(
        models.QuizQuestion.question_uuid == quiz_uuid,
        models.QuizQuestion.status == True
    ).options(selectinload(models.QuizQuestion.options))
    
    result = await db.execute(query)
    question = result.scalars().first()
    
    if not question:
        return JSONResponse(status_code=404, content={"success": False, "message": "Quiz not found"})
        
    # Relational Maps
    cat_result = await db.execute(select(models.Category).filter(models.Category.id == question.category_id))
    category = cat_result.scalars().first()
    
    lang_result = await db.execute(select(models.Language).filter(models.Language.id == question.language_id))
    language = lang_result.scalars().first()
    
    bv_result = await db.execute(select(models.BibleVersion).filter(models.BibleVersion.id == question.bible_version_id))
    bible_version = bv_result.scalars().first()
    
    target_language_name = "Target Language"
    if target_language_id:
        target_lang_res = await db.execute(select(models.Language).filter(models.Language.id == target_language_id))
        target_lang = target_lang_res.scalars().first()
        if target_lang:
            target_language_name = target_lang.name

    # Decipher Option logic
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
            "source_language": language.name if language else "Unknown",
            "target_language": target_language_name,
            "category_name": category.name if category else "Unknown",
            "bible_version": bible_version.short_name if bible_version else "Unknown",
            "question": question.question,
            "option_a": option_map.get("option_a", ""),
            "option_b": option_map.get("option_b", ""),
            "option_c": option_map.get("option_c", ""),
            "option_d": option_map.get("option_d", ""),
            "correct_option": correct_option,
            "answer_explanation": question.answer_reason or "",
            "bible_reference": question.bible_reference or ""
        }
    }

@router.post("/submit", response_model=schemas.SubmitTranslationResponse)
async def submit_translation(
    request: schemas.SubmitTranslationRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate quiz exists
    quiz_query = select(models.QuizQuestion).filter(models.QuizQuestion.question_uuid == request.quiz_uuid)
    quiz_result = await db.execute(quiz_query)
    quiz = quiz_result.scalars().first()
    if not quiz:
        return JSONResponse(status_code=400, content={"success": False, "message": "Original quiz not found"})

    # Validate target language exists
    lang_query = select(models.Language).filter(models.Language.id == request.target_language_id)
    lang_result = await db.execute(lang_query)
    target_lang = lang_result.scalars().first()
    if not target_lang:
        return JSONResponse(status_code=400, content={"success": False, "message": "Target language not found"})

    # Check for duplicate translation for this specific language
    dup_query = select(models.QuizTranslation).filter(
        models.QuizTranslation.quiz_uuid == request.quiz_uuid,
        models.QuizTranslation.target_language_id == request.target_language_id
    )
    dup_result = await db.execute(dup_query)
    if dup_result.scalars().first():
        return JSONResponse(status_code=409, content={"success": False, "message": "Translation already exists"})

    # Save translation
    translation_uuid = f"trans_{uuid.uuid4().hex}"
    new_translation = models.QuizTranslation(
        translation_uuid=translation_uuid,
        quiz_uuid=request.quiz_uuid,
        translator_user_id=current_user.id,
        source_language_id=request.source_language_id,
        target_language_id=request.target_language_id,
        translated_question=request.translated_question,
        translated_option_a=request.translated_option_a,
        translated_option_b=request.translated_option_b,
        translated_option_c=request.translated_option_c,
        translated_option_d=request.translated_option_d,
        translated_correct_option=request.translated_correct_option,
        translated_answer_explanation=request.translated_answer_explanation,
        review_status="pending"
    )
    db.add(new_translation)
    await db.commit()

    return {
        "success": True,
        "message": "Translation submitted successfully",
        "translation_uuid": translation_uuid,
        "review_status": "pending"
    }

@router.get("/my-translations", response_model=schemas.MyTranslationsResponse)
async def get_my_translations(
    page: int = 1,
    limit: int = 10,
    review_status: Optional[str] = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    query = select(models.QuizTranslation).filter(models.QuizTranslation.translator_user_id == current_user.id)
    
    if review_status and review_status in ["pending", "approved", "rejected"]:
        query = query.filter(models.QuizTranslation.review_status == review_status)
        
    total_records_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_records = total_records_result.scalar() or 0
    
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    offset = (page - 1) * limit
    paginated_query = query.order_by(models.QuizTranslation.created_at.desc()).offset(offset).limit(limit)
    
    translations_result = await db.execute(paginated_query)
    translations = translations_result.scalars().all()
    
    lang_result = await db.execute(select(models.Language))
    languages_map = {l.id: l.name for l in lang_result.scalars().all()}
    
    # Needs to trace back to original question
    quiz_uuids = [t.quiz_uuid for t in translations]
    questions_map = {}
    if quiz_uuids:
        q_result = await db.execute(select(models.QuizQuestion).filter(models.QuizQuestion.question_uuid.in_(quiz_uuids)))
        for q in q_result.scalars().all():
            questions_map[q.question_uuid] = q.question
    
    data = []
    for t in translations:
        data.append({
            "translation_uuid": t.translation_uuid,
            "quiz_uuid": t.quiz_uuid,
            "question": questions_map.get(t.quiz_uuid, "Unknown Question"),
            "target_language": languages_map.get(t.target_language_id, "Unknown"),
            "review_status": t.review_status,
            "review_comment": t.review_comment,
            "submitted_at": t.created_at
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
