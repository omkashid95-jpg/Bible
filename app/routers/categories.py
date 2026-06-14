from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app import schemas, models, database, dependencies

from fastapi.responses import JSONResponse

router = APIRouter(tags=["Categories"])

@router.get("/api/v1/quiz/categories", response_model=schemas.QuizCategoryListResponse)
async def get_quiz_categories(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Category))
    categories = result.scalars().all()
    
    # Map the database categories to the required response schema
    mapped_categories = [
        {
            "id": cat.uuid,
            "name": cat.name,
            "image_url": cat.image_url or ""
        }
        for cat in categories
    ]
    
    return {"categories": mapped_categories}

@router.get("/api/v1/categories/{category_id}", response_model=schemas.CategoryDetailResponse)
async def get_category_details(
    category_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # 1. Verify category exists
    result = await db.execute(select(models.Category).filter(models.Category.id == category_id))
    category = result.scalars().first()
    
    if not category:
        return JSONResponse(status_code=404, content={"success": False, "message": "Category not found"})
        
    # 2. Count quizzes under category (counting questions for now to satisfy mock logic)
    # This queries the questions table for the category
    q_result = await db.execute(select(models.Question).filter(models.Question.category_id == category.id))
    questions = q_result.scalars().all()
    
    # 3. Formulate response
    return {
        "success": True,
        "data": {
            "id": category.id,
            "uuid": category.uuid,
            "name": category.name,
            "description": category.description or "",
            "icon_url": category.icon_url or "",
            "image_url": category.image_url or "",
            "total_quizzes": len(questions) // 10 if len(questions) > 10 else 1, # Approximating quizzes
            "total_questions": len(questions),
            "status": category.status
        }
    }
