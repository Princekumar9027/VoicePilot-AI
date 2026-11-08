import secrets

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.session import Base, SessionLocal, engine
from app.models.entities import User

ADMIN_EMAIL = "admin@voicepilot.local"


def main() -> None:
    settings = get_settings()
    if settings.environment != "development":
        print("Seeding is only allowed when ENVIRONMENT=development")
        return
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == ADMIN_EMAIL)):
            print(f"{ADMIN_EMAIL} already exists")
            return
        password = settings.seed_admin_password or f"Vp!{secrets.token_urlsafe(9)}"
        db.add(
            User(
                email=ADMIN_EMAIL,
                full_name="Developer Admin",
                password_hash=hash_password(password),
                role="ADMIN",
                email_verified=True,
            )
        )
        db.commit()
        print(f"Created {ADMIN_EMAIL}")
        print(f"Password: {password}")


if __name__ == "__main__":
    main()
