"""Auth profile routes — profile update, location, logout."""
import logging
import os
import re
from typing import Optional
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import User
from dependencies import get_current_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    zip_code: Optional[str] = None


class ProfileUpdateResponse(BaseModel):
    status: str
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    zip_code: Optional[str] = None
    profile_complete: bool = False


@router.patch("/auth/profile", response_model=ProfileUpdateResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Update user profile (name, email, company). Required before sending outreach."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await session.get(User, auth_session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.name is not None:
        user.name = body.name.strip()
    if body.email is not None:
        user.email = body.email.strip().lower()
    if body.company is not None:
        user.company = body.company.strip()
    if body.zip_code is not None:
        user.zip_code = body.zip_code.strip()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return ProfileUpdateResponse(
        status="ok",
        name=user.name,
        email=user.email,
        company=user.company,
        zip_code=user.zip_code,
        profile_complete=bool(user.name and user.email),
    )


class LocationRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zip_code: Optional[str] = None


class LocationResponse(BaseModel):
    status: str
    zip_code: Optional[str] = None


@router.post("/auth/location", response_model=LocationResponse)
async def set_user_location(
    body: LocationRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Set user location from GPS coordinates (reverse-geocoded) or manual zip code."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await session.get(User, auth_session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    zip_code = body.zip_code

    # Reverse-geocode lat/lng → zip code if GPS coordinates provided
    if not zip_code and body.latitude is not None and body.longitude is not None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.bigdatacloud.net/data/reverse-geocode-client",
                    params={"latitude": body.latitude, "longitude": body.longitude, "localityLanguage": "en"},
                )
                resp.raise_for_status()
                data = resp.json()
                zip_code = data.get("postcode") or None
        except Exception as e:
            logger.warning(f"[Auth] Reverse geocode failed: {e}")

    if not zip_code:
        raise HTTPException(status_code=400, detail="Could not determine zip code. Please enter it manually.")

    # Validate zip format (5-digit US zip)
    zip_code = zip_code.strip()
    if not re.match(r'^\d{5}$', zip_code):
        raise HTTPException(status_code=400, detail="Invalid zip code format. Please enter a 5-digit US zip code.")

    user.zip_code = zip_code
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return LocationResponse(status="ok", zip_code=user.zip_code)


@router.post("/auth/logout")
async def auth_logout(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Revoke the current session."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    auth_session.revoked_at = datetime.utcnow()
    session.add(auth_session)
    await session.commit()
    
    return {"status": "ok"}
