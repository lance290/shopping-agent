import pytest
from services.llm import make_pop_decision, ChatContext
import json

@pytest.mark.asyncio
async def test_pop_intent_replace_item():
    ctx = ChatContext(
        user_message="make one of the cheeses a roquefort",
        conversation_history=[
            {"role": "user", "content": "cheese and charcuterie plate"},
            {"role": "assistant", "content": "Added cheese and charcuterie plate"}
        ],
        active_row={"id": 1, "title": "Cheese", "constraints": {}},
        active_project={"id": 1, "title": "My List"},
        pending_clarification=None
    )
    decision = await make_pop_decision(ctx)
    print(decision.action, decision.intent.what)
    assert decision.action["type"] in ("update_row", "delete_row", "create_row")

@pytest.mark.asyncio
async def test_pop_intent_delete_item():
    ctx = ChatContext(
        user_message="no - one of the cheeses, not the charcuteries",
        conversation_history=[
            {"role": "user", "content": "make one of the cheeses a roquefort"},
            {"role": "assistant", "content": "I've updated the charcuterie plate to include Roquefort"}
        ],
        active_row={"id": 2, "title": "Charcuterie Plate", "constraints": {}},
        active_project={"id": 1, "title": "My List"},
        pending_clarification=None
    )
    decision = await make_pop_decision(ctx)
    print(decision.action, decision.intent.what)
    assert decision.action["type"] == "delete_row"
