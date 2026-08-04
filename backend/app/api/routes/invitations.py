"""Scanner-safe invitation completion endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.dependencies.identity import CurrentIdentity, require_csrf
from app.services.invitation_service import InvitationError, InvitationService

router = APIRouter()

class InvitationIntentRequest(BaseModel):
    intent: str

@router.get('/invitations/verify')
def verify_invitation(token: str = Query(...)):
    try:
        _, intent = InvitationService().verify_token(token)
    except InvitationError:
        return RedirectResponse('/invitations/accept?error=invalid', status_code=303)
    return RedirectResponse(f'/invitations/accept?intent={intent}', status_code=303)

@router.post('/invitations/accept')
def accept_invitation(request: InvitationIntentRequest, current: CurrentIdentity = Depends(require_csrf)):
    try:
        return InvitationService().accept(intent=request.intent, user=current.user)
    except InvitationError as exc:
        code = str(exc)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN if code == 'invitation_email_mismatch' else status.HTTP_404_NOT_FOUND, detail=code) from exc

@router.post('/invitations/decline')
def decline_invitation(request: InvitationIntentRequest, current: CurrentIdentity = Depends(require_csrf)):
    try:
        return InvitationService().decline(intent=request.intent, user=current.user)
    except InvitationError as exc:
        code = str(exc)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN if code == 'invitation_email_mismatch' else status.HTTP_404_NOT_FOUND, detail=code) from exc
