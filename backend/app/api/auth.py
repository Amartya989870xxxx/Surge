from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import get_services
from app.auth.deps import require_user
from app.db.models import User
from app.services import Services

router = APIRouter(prefix="/api/auth", tags=["auth"])

PERSONAS = {"founder", "student", "engineer", "designer", "marketer", "other"}


class ProfileOut(BaseModel):
    id: str
    email: str | None
    display_name: str | None
    picture_url: str | None
    persona: str | None
    persona_label: str | None
    goal: str | None
    goal_template: str | None
    answers: dict[str, Any]
    onboarding_completed: bool


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    persona: str | None = None
    persona_label: str | None = Field(default=None, max_length=120)
    goal: str | None = Field(default=None, max_length=2000)
    goal_template: str | None = Field(default=None, max_length=120)
    answers: dict[str, Any] | None = None
    onboarding_completed: bool | None = None

    @field_validator("persona")
    @classmethod
    def _valid_persona(cls, value: str | None) -> str | None:
        if value is not None and value not in PERSONAS:
            raise ValueError(f"persona must be one of {sorted(PERSONAS)}")
        return value


def _out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "picture_url": user.picture_url,
        "persona": user.persona,
        "persona_label": user.persona_label,
        "goal": user.goal,
        "goal_template": user.goal_template,
        "answers": user.answers or {},
        "onboarding_completed": user.onboarding_completed,
    }


@router.get("/me", response_model=ProfileOut)
async def me(user: User = Depends(require_user)):
    return _out(user)


@router.put("/profile", response_model=ProfileOut)
async def update_profile(body: ProfileUpdate, user: User = Depends(require_user), services: Services = Depends(get_services)):
    fields = body.model_dump(exclude_unset=True)
    updated = services.users.update_profile(user.id, **fields)
    return _out(updated)
