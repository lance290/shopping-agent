import asyncio
from database import get_session
from models import User, AuthSession
from main import hash_token
from sqlmodel import select

async def mint_session():
    async for session in get_session():
        email = "bff_test@example.com"
        token = "test_token_123"
        
        # Create User
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            user = User(email=email)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
        # Create Session
        auth_session = AuthSession(
            email=email,
            user_id=user.id,
            session_token_hash=hash_token(token)
        )
        session.add(auth_session)
        await session.commit()
        print(f"MINTED_TOKEN:{token}")
        return

if __name__ == "__main__":
    asyncio.run(mint_session())
