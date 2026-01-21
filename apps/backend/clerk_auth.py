"""
Clerk JWT verification for backend authentication.
Verifies JWTs issued by Clerk using their JWKS endpoint.
"""
import os
import httpx
import jwt
from jwt import PyJWKClient
from typing import Optional
from functools import lru_cache

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")

# Extract the Clerk instance ID from the publishable key
# Format: pk_test_<base64_encoded_instance>.clerk.accounts.dev$
def get_clerk_instance() -> str:
    """Extract Clerk instance from publishable key."""
    if not CLERK_PUBLISHABLE_KEY:
        return ""
    try:
        # Remove pk_test_ or pk_live_ prefix
        key_part = CLERK_PUBLISHABLE_KEY.split("_", 2)[-1]
        # The instance is base64 encoded before the $
        import base64
        if "$" in key_part:
            key_part = key_part.split("$")[0]
        decoded = base64.b64decode(key_part + "==").decode("utf-8")
        # Remove any trailing $ or whitespace
        decoded = decoded.rstrip("$").strip()
        return decoded
    except Exception:
        return ""


@lru_cache(maxsize=1)
def get_jwks_client() -> Optional[PyJWKClient]:
    """Get cached JWKS client for Clerk."""
    instance = get_clerk_instance()
    if not instance:
        print("[CLERK] No Clerk instance found, falling back to secret key verification")
        return None
    
    # Clerk JWKS URL format
    jwks_url = f"https://{instance}/.well-known/jwks.json"
    print(f"[CLERK] Using JWKS URL: {jwks_url}")
    
    try:
        return PyJWKClient(jwks_url)
    except Exception as e:
        print(f"[CLERK] Failed to create JWKS client: {e}")
        return None


def verify_clerk_token(token: str) -> Optional[dict]:
    """
    Verify a Clerk JWT token and return the decoded payload.
    Returns None if verification fails.
    """
    if not token:
        return None
    
    try:
        # Try JWKS verification first
        jwks_client = get_jwks_client()
        if jwks_client:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False}  # Clerk doesn't always set audience
            )
            return decoded
        
        # Fallback: verify with secret key (HS256)
        if CLERK_SECRET_KEY:
            decoded = jwt.decode(
                token,
                CLERK_SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            return decoded
        
        print("[CLERK] No verification method available")
        return None
        
    except jwt.ExpiredSignatureError:
        print("[CLERK] Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"[CLERK] Invalid token: {e}")
        return None
    except Exception as e:
        print(f"[CLERK] Verification error: {e}")
        return None


def get_clerk_user_id(token: str) -> Optional[str]:
    """Extract Clerk user ID from token."""
    payload = verify_clerk_token(token)
    if payload:
        # Clerk stores user ID in 'sub' claim
        return payload.get("sub")
    return None
