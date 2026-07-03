from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.consent_repository import ConsentRepository
from app.schemas.consent import ConsentGrantRequest, ConsentRecordResponse, EffectiveConsentResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/consent", tags=["consent"])


async def _resolve_user_id(current_user: CurrentUser, db: AsyncSession):
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.get("/", response_model=EffectiveConsentResponse, summary="Get effective consent state")
async def get_consent(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EffectiveConsentResponse:
    user_id = await _resolve_user_id(current_user, db)
    repo = ConsentRepository(db)
    effective = await repo.get_effective(user_id)
    return EffectiveConsentResponse(consents=effective)


@router.post("/", response_model=ConsentRecordResponse, status_code=201, summary="Record a consent decision")
async def record_consent(
    body: ConsentGrantRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ConsentRecordResponse:
    user_id = await _resolve_user_id(current_user, db)
    repo = ConsentRepository(db)
    entry = await repo.record(
        user_id=user_id,
        consent_type=body.consent_type,
        granted=body.granted,
        source=body.source,
    )
    return ConsentRecordResponse.model_validate(entry)


@router.delete("/audio", status_code=204, summary="Revoke all audio consent and request data deletion")
async def revoke_audio_consent(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Revokes both audio_storage and audio_training consent.
    Records revocation events. Actual data deletion is handled by the privacy/data-deletion flow.
    """
    user_id = await _resolve_user_id(current_user, db)
    repo = ConsentRepository(db)
    await repo.record(user_id=user_id, consent_type="audio_storage", granted=False, source="revoke_audio")
    await repo.record(user_id=user_id, consent_type="audio_training", granted=False, source="revoke_audio")
