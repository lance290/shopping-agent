from routes.chat import _should_force_context_switch


def test_forces_switch_for_clear_topic_change():
    assert _should_force_context_switch(
        user_message="yacht charter",
        active_row_title="Roblox gift card",
        pending_clarification=None,
    ) is True


def test_does_not_switch_for_price_refinement():
    assert _should_force_context_switch(
        user_message="over $50 please",
        active_row_title="Roblox gift card",
        pending_clarification=None,
    ) is False


def test_does_not_switch_for_short_detail_message():
    assert _should_force_context_switch(
        user_message="tomorrow",
        active_row_title="private jet charter",
        pending_clarification=None,
    ) is False


def test_does_not_switch_when_pending_clarification_exists():
    assert _should_force_context_switch(
        user_message="yacht charter",
        active_row_title="Roblox gift card",
        pending_clarification={"type": "clarification"},
    ) is False


def test_does_not_switch_when_topics_overlap():
    assert _should_force_context_switch(
        user_message="roblox gift cards over 50",
        active_row_title="Roblox gift card",
        pending_clarification=None,
    ) is False
