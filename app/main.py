from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import auth, users, categories, questions, quizzes, leaderboard, profile, user, home, challenges, create_quiz, translate_quiz, correction_quiz, groups, notifications, rewards, referrals, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Bible Quiz API",
    description="Backend API for a Bible Quiz Application",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(user.router)
app.include_router(profile.router)
app.include_router(home.router)
app.include_router(challenges.router)
app.include_router(create_quiz.router)
app.include_router(translate_quiz.router)
app.include_router(correction_quiz.router)
app.include_router(groups.router)
app.include_router(notifications.router)
app.include_router(rewards.router)
app.include_router(referrals.router)
app.include_router(admin.router)
app.include_router(categories.router)
app.include_router(questions.router)
app.include_router(quizzes.router)
app.include_router(leaderboard.router)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Unauthorized"}
        )
    # Default behavior for other HTTPExceptions
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.get("/")
async def root():
    return {"message": "Welcome to the Bible Quiz API. Visit /docs for documentation."}
