import asyncio
import json
import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
import sys

sys.path.append(".")
from services.llm import make_unified_decision, ChatContext

async def main():
    ctx = ChatContext(
        user_message="Yes, personalized",
        conversation_history=[
            {"role": "user", "content": "I need a present for my wife"},
            {"role": "assistant", "content": "Would you like it personalized?"},
            {"role": "user", "content": "Yes, personalized"}
        ],
        active_row=None,
        active_project=None,
        pending_clarification={
            "type": "clarification",
            "title": "Anniversary gift",
            "partial_constraints": {}
        }
    )
    decision = await make_unified_decision(ctx)
    print("Decision intent:", decision.intent)
    print("Decision action:", decision.action)

if __name__ == "__main__":
    asyncio.run(main())
