"""Authentication router."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.security import hash_password
from backend.database import get_db
from backend.models.user import User
from backend.schemas.auth import UserResponse, UserSignup

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserSignup,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Create a new user account.

    Args:
        user_data: User signup data (email, password, name)
        db: Database session

    Returns:
        UserResponse: Created user information

    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        id=uuid4(),
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
        role="user",
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        created_at=new_user.created_at.isoformat(),
    )
