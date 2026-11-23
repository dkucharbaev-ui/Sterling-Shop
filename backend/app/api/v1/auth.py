from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.dependencies import get_current_user
from app.core.logger import logger
from app.core.security import create_access_token, validate_telegram_init_data
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AuthInitDataRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/telegram", response_model=TokenResponse)
async def auth_telegram(
    payload: AuthInitDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates a user via Telegram WebApp initData string.
    Validates HMAC signature and creates/updates the user profile.
    """
    try:
        tg_user = validate_telegram_init_data(
            init_data=payload.init_data,
            bot_token=settings.BOT_TOKEN,
        )
    except ValueError as e:
        logger.warning("auth_failed_invalid_init_data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Telegram authentication failed: {str(e)}",
        )

    # Upsert user in database
    result = await db.execute(select(User).where(User.id == tg_user.id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=tg_user.id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            username=tg_user.username,
            language_code=tg_user.language_code,
            is_premium=bool(tg_user.is_premium),
        )
        db.add(user)
        logger.info("new_user_registered", user_id=user.id, username=user.username)
    else:
        # Update details if changed
        user.first_name = tg_user.first_name
        user.last_name = tg_user.last_name
        user.username = tg_user.username
        user.language_code = tg_user.language_code
        user.is_premium = bool(tg_user.is_premium)

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been blocked",
        )

    await db.commit()
    await db.refresh(user)

    is_admin = user.id in settings.admin_ids
    token = create_access_token(
        subject=user.id,
        extra_claims={
            "username": user.username,
            "is_admin": is_admin,
        },
    )

    user_response = UserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        is_premium=user.is_premium,
        is_blocked=user.is_blocked,
        is_admin=is_admin,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_response,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Returns current authenticated user profile.
    """
    return UserResponse(
        id=current_user.id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        username=current_user.username,
        is_premium=current_user.is_premium,
        is_blocked=current_user.is_blocked,
        is_admin=current_user.id in settings.admin_ids,
    )
