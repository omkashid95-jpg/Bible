# Bible Quiz Backend API

A complete production-ready backend for a Bible Quiz App built with Python, FastAPI, SQLAlchemy (Async), and SQLite.

## Features

- **JWT Authentication**: User signup, login, and secure routes.
- **Async Database**: Uses SQLAlchemy AsyncORM with SQLite.
- **RESTful Endpoints**: Full CRUD for Categories, Questions.
- **Quiz Engine**: Submit quiz answers and auto-calculate scores.
- **Leaderboard**: Global ranking based on user scores.

## Setup Instructions

1. **Clone the repository or navigate to the project directory:**
   ```bash
   cd d:/python/bible
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   A `.env` file is already provided. You can modify it if needed:
   ```env
   SECRET_KEY=a_very_secret_key_for_jwt_auth_change_in_production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   DATABASE_URL=sqlite+aiosqlite:///./bible_quiz.db
   ```

5. **Seed the Database with Sample Data:**
   Run the seed script to create tables and insert dummy categories and questions.
   ```bash
   python seed_data.py
   ```
   *Note: This will drop existing tables if they exist and recreate them.*
   *Test User credentials generated:* `testuser` / `password123`

6. **Run the Development Server:**
   ```bash
   uvicorn app.main:app --reload
   ```

7. **API Documentation:**
   Open your browser and navigate to:
   - **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Project Structure

```text
bible/
├── app/
│   ├── routers/
│   │   ├── auth.py         # Login and signup routes
│   │   ├── users.py        # User profile routes
│   │   ├── categories.py   # Quiz categories
│   │   ├── questions.py    # Questions management
│   │   ├── quizzes.py      # Quiz submission and attempts
│   │   └── leaderboard.py  # Global ranking
│   ├── auth.py             # JWT & Password hashing
│   ├── config.py           # Environment config (Pydantic)
│   ├── database.py         # Async SQLite connection
│   ├── dependencies.py     # FastAPI dependencies (auth)
│   ├── main.py             # FastAPI entry point
│   ├── models.py           # SQLAlchemy ORM models
│   └── schemas.py          # Pydantic validation schemas
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── seed_data.py            # Database seeder script
└── README.md               # Project documentation
```
