import re

class SafetyService:
    # Categories that are hard-blocked (illegal, highly abusive)
    BLOCKED_PATTERNS = [
        r"\b(cp|csam)\b",
        r"\b(underage|minor|child)\s+(sex|escort|companion)\b",
        r"\b(hitman|murder|kill)\s+for\s+hire\b",
        r"\bhire\s+(a\s+)?hitman\b",
        r"\b(bomb|explosive)\s+making\b",
        r"\b(meth|heroin|fentanyl|cocaine)\b",
        r"\b(trafficking|smuggling)\b",
    ]

    # Categories that are high-risk/sensitive (require manual review/confirmation)
    SENSITIVE_PATTERNS = [
        r"\b(escort|companion|massage|body\s*rub)\b",
        r"\b(adult|xxx|porn)\b",
        r"\b(weapon|firearm|gun|ammo)\b",
        r"\b(drug|pill|prescription)\b",
        r"\bcupcakes?\b", # Context-dependent example from user
    ]

    @staticmethod
    def check_safety(query: str) -> dict:
        """
        Checks a query against safety rules.
        Returns:
            {
                "status": "safe" | "needs_review" | "blocked",
                "reason": str | None
            }
        """
        query_lower = query.lower()

        # Check blocked patterns first
        for pattern in SafetyService.BLOCKED_PATTERNS:
            if re.search(pattern, query_lower):
                return {
                    "status": "blocked",
                    "reason": "This request violates our safety policies."
                }

        # Check sensitive patterns
        for pattern in SafetyService.SENSITIVE_PATTERNS:
            if re.search(pattern, query_lower):
                return {
                    "status": "needs_review",
                    "reason": "This request involves a sensitive category and requires manual verification."
                }

        return {"status": "safe", "reason": None}
