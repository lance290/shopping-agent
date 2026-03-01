import asyncio
from services.llm import make_pop_decision, ChatContext

async def main():
    ctx = ChatContext(
        user_message="ice cream, cookies, and wine please",
        conversation_history=[
            {"role": "assistant", "content": "Hey! I'm Pop, your grocery savings assistant. Tell me what you need from the store and I'll find the best deals for you. Try something like \"I need milk, eggs, and bread\"."}
        ],
        active_row=None,
        active_project={"id": 1, "title": "Family Shopping List"},
    )
    decision = await make_pop_decision(ctx)
    print("Action:", decision.action)
    print("Items:", decision.items)

asyncio.run(main())
