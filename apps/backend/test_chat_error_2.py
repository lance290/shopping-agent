import asyncio
from services.llm import make_unified_decision, ChatContext

async def main():
    ctx = ChatContext(
        user_message="Yes, personalized",
        conversation_history=[
            {"role": "user", "content": "I need a present for my wife for our silver anniversary"},
            {"role": "assistant", "content": "Would you like something that could be personalized or engraved?"},
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
