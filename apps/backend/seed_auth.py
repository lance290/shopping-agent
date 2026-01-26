import asyncio
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from models import User, AuthSession, hash_token
from database import engine

async def seed_user():
    token = "aHLQEBCyuUiluZmJO12ao1OsJr2gX2ZSc8HK6YMnLTg"
    token_hash = hash_token(token)
    
    async with AsyncSession(engine) as session:
        # Check if user exists
        stmt = select(User).where(User.email == "dev@example.com")
        result = await session.exec(stmt)
        existing_user = result.first()
        
        if not existing_user:
            print("Creating dev user...")
            user = User(email="dev@example.com", is_active=True)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id
        else:
            print("Dev user exists.")
            user_id = existing_user.id
            
        # Check auth session
        stmt = select(AuthSession).where(AuthSession.session_token_hash == token_hash)
        result = await session.exec(stmt)
        existing_auth = result.first()
        
        if not existing_auth:
            print("Creating auth session...")
            auth = AuthSession(
                user_id=user_id,
                email="dev@example.com",
                session_token_hash=token_hash,
                created_at=datetime.utcnow()
            )
            session.add(auth)
            await session.commit()
            print("Auth session created.")
        else:
            print("Auth session exists.")

if __name__ == "__main__":
    asyncio.run(seed_user())
