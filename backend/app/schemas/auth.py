from pydantic import BaseModel


class MeResponse(BaseModel):
    uid: str
    email: str | None
    role: str
    email_verified: bool
