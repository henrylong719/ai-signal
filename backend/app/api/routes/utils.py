from fastapi import APIRouter, Depends, HTTPException
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser
from app.schemas import Message
from app.services.email import send_test_email

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """Send a test email via Resend.

    Used by operators to confirm Resend credentials and the
    ``EMAILS_FROM_EMAIL`` sender are wired up correctly. Surfaces
    the Resend error string in the 502 detail so a misconfigured
    deploy is debuggable from a single API call instead of having
    to grep logs.
    """
    result = send_test_email(email_to=email_to)
    if not result.ok:
        raise HTTPException(
            status_code=502,
            detail=f"Resend rejected the test email: {result.error}",
        )
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    return True
