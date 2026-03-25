from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TOTPLoginRequest(BaseModel):
    session_token: str
    totp_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TOTPRequiredResponse(BaseModel):
    totp_required: bool = True
    session_token: str


class UserInfo(BaseModel):
    id: str
    username: str
    totp_enabled: bool


class TOTPSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_png_b64: str


class TOTPConfirmRequest(BaseModel):
    totp_code: str


class SuccessResponse(BaseModel):
    success: bool = True


class ChangeProfileRequest(BaseModel):
    current_password: str
    new_username: str | None = None
    new_password: str | None = None
