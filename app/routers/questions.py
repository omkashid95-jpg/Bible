from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app import schemas, models, database, dependencies

router = APIRouter(prefix="/questions", tags=["Questions"])

@router.get("/category/{category_id}", response_model=List[schemas.QuestionResponse])
async def get_questions_by_category(category_id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Question).filter(models.Question.category_id == category_id))
    return result.scalars().all()

@router.post("/", response_model=schemas.QuestionResponse)
async def create_question(question: schemas.QuestionCreate, db: AsyncSession = Depends(database.get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    new_question = models.Question(**question.model_dump())
    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)
    return new_question
