# Assumptions — enhancement-bug-report-triage

1. Existing LLM client can be reused in `bugs.py` for classification.
2. Resend is configured in production (RESEND_API_KEY present) for email delivery.
3. Confidence threshold default of 0.7 is acceptable and can be tuned later.
4. Hardcoded email recipient (masseyl@gmail.com) is acceptable for MVP.
