import asyncio
from app.database import engine, SessionLocal, Base
from app.models import Category, Question
from app.auth import get_password_hash
from app.models import User

async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=get_password_hash("password123")
        )
        db.add(user)

        ot_cat = Category(name="Old Testament", description="Questions from the Old Testament")
        nt_cat = Category(name="New Testament", description="Questions from the New Testament")
        db.add_all([ot_cat, nt_cat])
        await db.commit()
        await db.refresh(ot_cat)
        await db.refresh(nt_cat)

        questions = [
            Question(
                category_id=ot_cat.id, text="Who built the ark?",
                option_a="Moses", option_b="Noah", option_c="Abraham", option_d="David",
                correct_option="B"
            ),
            Question(
                category_id=ot_cat.id, text="Who was swallowed by a great fish?",
                option_a="Jonah", option_b="Job", option_c="Peter", option_d="Paul",
                correct_option="A"
            ),
            Question(
                category_id=nt_cat.id, text="Where was Jesus born?",
                option_a="Jerusalem", option_b="Nazareth", option_c="Bethlehem", option_d="Jericho",
                correct_option="C"
            ),
            Question(
                category_id=nt_cat.id, text="Who betrayed Jesus?",
                option_a="Peter", option_b="John", option_c="Judas Iscariot", option_d="Thomas",
                correct_option="C"
            )
        ]
        db.add_all(questions)
        await db.commit()

    print("Database seeded successfully with sample data!")

if __name__ == "__main__":
    asyncio.run(seed_database())
