from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
import uuid
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/api/v1/quiz", tags=["Quizzes"])

@router.post("/start", response_model=schemas.StartQuizResponse)
async def start_quiz(
    request: schemas.StartQuizRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate category exists
    cat_result = await db.execute(select(models.Category).filter(models.Category.id == request.category_id))
    category = cat_result.scalars().first()
    if not category:
        raise HTTPException(status_code=400, detail="Invalid request")

    # Validate language exists
    lang_result = await db.execute(select(models.Language).filter(models.Language.id == request.language_id))
    language = lang_result.scalars().first()
    if not language:
        raise HTTPException(status_code=400, detail="Invalid request")

    # Validate bible version exists
    bv_result = await db.execute(select(models.BibleVersion).filter(models.BibleVersion.id == request.bible_version_id))
    bible_version = bv_result.scalars().first()
    if not bible_version:
        raise HTTPException(status_code=400, detail="Invalid request")

    # Fetch quiz questions
    q_result = await db.execute(select(models.Question).filter(models.Question.category_id == category.id))
    questions = q_result.scalars().all()
    if not questions:
        return JSONResponse(status_code=404, content={"success": False, "message": "No questions available for selected criteria"})

    # Create quiz session
    session_uuid = f"quiz_session_{uuid.uuid4().hex}"
    
    new_session = models.QuizSession(
        session_uuid=session_uuid,
        user_id=current_user.id,
        category_id=category.id,
        language_id=language.id,
        bible_version_id=bible_version.id,
        mode=request.mode,
        total_questions=len(questions),
        score=0,
        status="started"
    )
    db.add(new_session)
    await db.commit()
    
    return {
        "success": True,
        "data": {
            "session_uuid": session_uuid,
            "category_id": category.id,
            "language_id": language.id,
            "bible_version_id": bible_version.id,
            "mode": request.mode,
            "total_questions": len(questions),
            "score": 0,
            "status": "started"
        }
    }

@router.get("/question/{session_uuid}", response_model=schemas.QuizQuestionResponse)
async def get_quiz_question(
    session_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate session
    session_result = await db.execute(select(models.QuizSession).filter(
        models.QuizSession.session_uuid == session_uuid,
        models.QuizSession.user_id == current_user.id
    ))
    session = session_result.scalars().first()
    if not session:
        return JSONResponse(status_code=404, content={"success": False, "message": "Quiz session not found"})

    # Fetch questions matching session configuration
    questions_result = await db.execute(select(models.QuizQuestion).filter(
        models.QuizQuestion.category_id == session.category_id,
        models.QuizQuestion.language_id == session.language_id,
        models.QuizQuestion.bible_version_id == session.bible_version_id
    ).options(selectinload(models.QuizQuestion.options)))
    questions = questions_result.scalars().all()

    if not questions or session.current_question_index >= len(questions):
        return JSONResponse(status_code=404, content={"success": False, "message": "No more questions available"})

    # Get current question
    current_question = questions[session.current_question_index]

    options_data = [
        {
            "option_id": opt.id,
            "option_text": opt.option_text
        } for opt in current_question.options
    ]

    return {
        "success": True,
        "data": {
            "question_uuid": current_question.question_uuid,
            "question_number": session.current_question_index + 1, # 1-indexed for the user interface
            "total_questions": session.total_questions,
            "question": current_question.question,
            "options": options_data
        }
    }

@router.get("/next-question/{session_uuid}", response_model=schemas.NextQuestionResponse)
async def get_next_question(
    session_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate session
    session_result = await db.execute(select(models.QuizSession).filter(
        models.QuizSession.session_uuid == session_uuid,
        models.QuizSession.user_id == current_user.id
    ))
    session = session_result.scalars().first()
    if not session:
        return JSONResponse(status_code=404, content={"success": False, "message": "Quiz session not found"})

    # Check if already completed
    if session.status == "completed":
        return {
            "success": True,
            "quiz_completed": True,
            "message": "Quiz completed successfully"
        }

    # Fetch questions matching session configuration
    questions_result = await db.execute(select(models.QuizQuestion).filter(
        models.QuizQuestion.category_id == session.category_id,
        models.QuizQuestion.language_id == session.language_id,
        models.QuizQuestion.bible_version_id == session.bible_version_id
    ).options(selectinload(models.QuizQuestion.options)))
    questions = questions_result.scalars().all()

    # Double check progression bounds
    if not questions or session.current_question_index >= len(questions) or session.current_question_index >= session.total_questions:
        if session.status != "completed":
            session.status = "completed"
            session.completed_at = func.now()
            await db.commit()
            
        return {
            "success": True,
            "quiz_completed": True,
            "message": "Quiz completed successfully"
        }

    # Get current question
    current_question = questions[session.current_question_index]

    options_data = [
        {
            "option_id": opt.id,
            "option_text": opt.option_text
        } for opt in current_question.options
    ]

    return {
        "success": True,
        "quiz_completed": False,
        "data": {
            "question_uuid": current_question.question_uuid,
            "question_number": session.current_question_index + 1,
            "total_questions": session.total_questions,
            "question": current_question.question,
            "options": options_data
        }
    }

@router.post("/answer", response_model=schemas.QuizAnswerResponse)
async def submit_quiz_answer(
    request: schemas.QuizAnswerRequest,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate session
    session_result = await db.execute(select(models.QuizSession).filter(
        models.QuizSession.session_uuid == request.session_uuid,
        models.QuizSession.user_id == current_user.id
    ))
    session = session_result.scalars().first()
    if not session:
        return JSONResponse(status_code=400, content={"success": False, "message": "Quiz session not found"})

    # Validate question
    question_result = await db.execute(select(models.QuizQuestion).filter(
        models.QuizQuestion.question_uuid == request.question_uuid
    ).options(selectinload(models.QuizQuestion.options)))
    question = question_result.scalars().first()
    
    if not question:
        return JSONResponse(status_code=404, content={"success": False, "message": "Invalid question"})

    # Check if question already answered
    existing_answer_result = await db.execute(select(models.QuizAnswer).filter(
        models.QuizAnswer.session_uuid == request.session_uuid,
        models.QuizAnswer.question_uuid == request.question_uuid
    ))
    if existing_answer_result.scalars().first():
        return JSONResponse(status_code=400, content={"success": False, "message": "Question already answered"})

    # Validate selected_option_id & check correct answer
    selected_option = None
    correct_option = None
    for opt in question.options:
        if opt.is_correct:
            correct_option = opt
        if opt.id == request.selected_option_id:
            selected_option = opt
            
    if not selected_option:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid option selected"})

    is_correct = selected_option.is_correct
    points_earned = 10 if is_correct else 0
    
    # Save answer record
    new_answer = models.QuizAnswer(
        answer_uuid=f"ans_{uuid.uuid4().hex}",
        session_uuid=session.session_uuid,
        user_id=current_user.id,
        question_uuid=question.question_uuid,
        selected_option_id=request.selected_option_id,
        is_correct=is_correct,
        points_earned=points_earned,
        time_taken_seconds=request.time_taken_seconds
    )
    db.add(new_answer)

    # Update quiz session score and progress
    session.score += points_earned
    session.current_question_index += 1
    
    # Determine completion
    answered_questions = session.current_question_index
    remaining_questions = session.total_questions - answered_questions
    quiz_completed = remaining_questions <= 0
    
    if quiz_completed:
        session.status = "completed"
        session.completed_at = func.now()

    await db.commit()

    return {
        "success": True,
        "data": {
            "is_correct": is_correct,
            "correct_option_id": correct_option.id if correct_option else 0,
            "points_earned": points_earned,
            "current_score": session.score,
            "answered_questions": answered_questions,
            "remaining_questions": remaining_questions,
            "quiz_completed": quiz_completed
        }
    }

@router.get("/result/{session_uuid}", response_model=schemas.QuizResultResponse)
async def get_quiz_result(
    session_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate session
    session_result = await db.execute(select(models.QuizSession).filter(
        models.QuizSession.session_uuid == session_uuid,
        models.QuizSession.user_id == current_user.id
    ))
    session = session_result.scalars().first()
    
    if not session:
        return JSONResponse(status_code=404, content={"success": False, "message": "Quiz session not found"})

    if session.status != "completed":
        return JSONResponse(status_code=400, content={"success": False, "message": "Quiz not completed yet"})

    # Fetch answers
    answers_result = await db.execute(select(models.QuizAnswer).filter(
        models.QuizAnswer.session_uuid == session_uuid
    ))
    answers = answers_result.scalars().all()

    # Calculate metrics
    correct_answers = sum(1 for a in answers if a.is_correct)
    wrong_answers = session.total_questions - correct_answers
    accuracy = (correct_answers / session.total_questions * 100.0) if session.total_questions > 0 else 0.0
    total_points = sum(a.points_earned for a in answers)
    total_time = sum(a.time_taken_seconds for a in answers)
    
    xp_earned = int(total_points * 0.5) # Dynamic XP calculation (50% of points)
    rank_change = 0 # Baseline

    # Update User Profile progression natively
    current_user.total_points += total_points
    current_user.total_score += total_points 
    
    # Simple dynamic level progression logic (100 XP threshold per level scale)
    if current_user.total_points >= (current_user.current_level * 100):
        current_user.current_level += 1
        rank_change = 1

    # Save to Quiz History if not already saved
    history_result = await db.execute(select(models.QuizHistory).filter(models.QuizHistory.session_uuid == session_uuid))
    if not history_result.scalars().first():
        new_history = models.QuizHistory(
            history_uuid=f"hist_{uuid.uuid4().hex}",
            session_uuid=session.session_uuid,
            user_id=current_user.id,
            category_id=session.category_id,
            score=session.score,
            total_questions=session.total_questions,
            correct_answers=correct_answers,
            accuracy_percentage=accuracy,
            points_earned=total_points,
            xp_earned=xp_earned,
            completed_at=session.completed_at
        )
        db.add(new_history)
        await db.commit()

    return {
        "success": True,
        "data": {
            "session_uuid": session.session_uuid,
            "score": session.score,
            "total_questions": session.total_questions,
            "correct_answers": correct_answers,
            "wrong_answers": wrong_answers,
            "accuracy_percentage": round(accuracy, 2),
            "total_points_earned": total_points,
            "xp_earned": xp_earned,
            "current_level": current_user.current_level,
            "rank_change": rank_change,
            "total_time_seconds": total_time,
            "completed_at": session.completed_at
        }
    }

@router.get("/review/{session_uuid}", response_model=schemas.QuizReviewResponse)
async def get_quiz_review(
    session_uuid: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Validate session
    session_result = await db.execute(select(models.QuizSession).filter(
        models.QuizSession.session_uuid == session_uuid,
        models.QuizSession.user_id == current_user.id
    ))
    session = session_result.scalars().first()
    
    if not session:
        return JSONResponse(status_code=404, content={"success": False, "message": "Quiz session not found"})

    # Fetch all answers for this session
    answers_result = await db.execute(select(models.QuizAnswer).filter(
        models.QuizAnswer.session_uuid == session_uuid
    ).order_by(models.QuizAnswer.answered_at.asc()))
    answers = answers_result.scalars().all()
    
    review_data = []
    
    for answer in answers:
        # Fetch question and its options
        question_result = await db.execute(select(models.QuizQuestion).filter(
            models.QuizQuestion.question_uuid == answer.question_uuid
        ).options(selectinload(models.QuizQuestion.options)))
        question = question_result.scalars().first()
        
        if not question:
            continue
            
        selected_option_text = ""
        correct_option_text = ""
        
        for opt in question.options:
            if opt.id == answer.selected_option_id:
                selected_option_text = opt.option_text
            if opt.is_correct:
                correct_option_text = opt.option_text
                
        review_data.append({
            "question_uuid": question.question_uuid,
            "question": question.question,
            "selected_option": selected_option_text,
            "correct_option": correct_option_text,
            "is_correct": answer.is_correct,
            "answer_explanation": question.answer_reason or "",
            "bible_reference": question.bible_reference or ""
        })

    return {
        "success": True,
        "data": review_data
    }

@router.get("/history", response_model=schemas.QuizHistoryResponse)
async def get_quiz_history(
    page: int = 1,
    limit: int = 10,
    category_id: int = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # Base query for history
    query = select(models.QuizHistory).filter(models.QuizHistory.user_id == current_user.id)
    
    # Filter by category if requested
    if category_id:
        query = query.filter(models.QuizHistory.category_id == category_id)
        
    # Get total records for pagination math
    total_records_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_records = total_records_result.scalar() or 0
    
    # Calculate pages
    import math
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
    
    # Apply pagination and sorting
    offset = (page - 1) * limit
    paginated_query = query.order_by(models.QuizHistory.completed_at.desc()).offset(offset).limit(limit)
    
    history_result = await db.execute(paginated_query)
    history_records = history_result.scalars().all()
    
    # Fetch all categories to map category names locally rather than complex joins for now
    categories_result = await db.execute(select(models.Category))
    categories_map = {c.id: c.name for c in categories_result.scalars().all()}
    
    data = []
    for record in history_records:
        data.append({
            "history_uuid": record.history_uuid,
            "session_uuid": record.session_uuid,
            "category_name": categories_map.get(record.category_id, "Unknown Category"),
            "score": record.score,
            "total_questions": record.total_questions,
            "accuracy_percentage": round(record.accuracy_percentage, 2),
            "points_earned": record.points_earned,
            "completed_at": record.completed_at
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

@router.get("/my-attempts", response_model=List[schemas.QuizAttemptResponse])
async def get_my_attempts(db: AsyncSession = Depends(database.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    result = await db.execute(select(models.QuizAttempt).filter(models.QuizAttempt.user_id == current_user.id).order_by(models.QuizAttempt.completed_at.desc()))
    return result.scalars().all()
