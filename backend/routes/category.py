from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.category import Category
from backend.schemas.category_create import CategoryCreate
from backend.schemas.category_read import CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate, db: Annotated[Session, Depends(get_db)]
) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
