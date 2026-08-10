from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class TOTPLoginRequest(BaseModel):
    session_token: str = Field(min_length=1, max_length=4096)
    totp_code: str = Field(pattern=r"^\d{6}$")


class TOTPRequiredResponse(BaseModel):
    totp_required: bool = True
    session_token: str


class UserInfo(BaseModel):
    id: str
    username: str
    totp_enabled: bool
    onboarding_completed: bool


class TOTPSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_png_b64: str


class TOTPConfirmRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    totp_code: str = Field(pattern=r"^\d{6}$")


class StepUpRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    current_totp_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class SuccessResponse(BaseModel):
    success: bool = True


class ChangeProfileRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_username: str | None = Field(default=None, min_length=1, max_length=64)
    new_password: str | None = Field(default=None, min_length=8, max_length=72)
