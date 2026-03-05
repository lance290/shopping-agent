# PRD: Phase 1 - Multimodal Inbound (The "Snap a Photo" Feature)

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
Penny AI heavily advertises its ability to build lists from fridge/pantry photos and recipe cards. To achieve parity and surpass them, PopSavings must process images received via SMS and Email. This phase involves extracting media from webhooks and passing it to our unified NLU engine, using vision models (e.g., Gemini 1.5 Pro or GPT-4o) to auto-extract grocery items.

## 2. Goals & Acceptance Criteria
- **Twilio MMS Parsing:** Extract `NumMedia` and `MediaUrlX` from Twilio inbound form data.
- **Resend Email Parsing:** Extract image attachments from Resend JSON payloads.
- **Vision LLM Routing:** Thread the image URLs through the `pop_processor` and into the `make_pop_decision` LLM prompt.
- **Acceptance Criteria:**
  - Sending an image-only SMS with a photo of a fridge results in the AI extracting visible grocery essentials and adding them as rows to the user's project.
  - Sending an email with a recipe image attachment results in parsed ingredient rows.
  - The fallback Gemini direct API gracefully handles (or safely ignores) images without crashing if OpenRouter vision models fail.

## 3. Scope
- **In-Scope:** 
  - Backend route updates (`routes/pop.py`).
  - NLU prompt updates to instruct the LLM to extract grocery items from images (`services/llm_pop.py`).
  - Core LLM client updates to support OpenAI-compatible multimodal message arrays (`services/llm_core.py`).
- **Out-of-Scope:** 
  - Frontend UI for uploading photos directly (this phase is strictly focused on inbound webhook channels SMS/Email).

## 4. Technical Implementation Notes
- **Twilio:** Use `request.form()` to parse `MediaUrl0`, `MediaContentType0`, etc. Handle scenarios where `Body` is empty but images are present by injecting a synthetic prompt (e.g., "Extract groceries from these images").
- **Resend:** Extract from the `attachments` array in the JSON payload, filtering for `image/*` content types.
- **Model Compatibility:** Ensure `OPENROUTER_MODEL` supports vision (e.g., `google/gemini-3-flash-preview` or `openai/gpt-4o`). The `messages` payload must be formatted as an array of content objects: `[{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}]`.
