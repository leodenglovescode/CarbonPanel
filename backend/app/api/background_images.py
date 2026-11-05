import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services import background_image_service as images
from app.services.settings_store import get_key, set_key

router = APIRouter(prefix="/settings/background-image", tags=["background-image"])
Target = Literal["app", "login", "android-app", "android-login"]
TARGETS = ("app", "login", "android-app", "android-login")
_lock = asyncio.Lock()


class Background(BaseModel):
    type: Literal["color", "gradient", "image"] = "color"
    gradientAngle: float = Field(default=135, ge=0, le=360)
    gradientStart: str = Field(default="#0d0d0d", pattern=r"^#[0-9a-fA-F]{6}$")
    gradientEnd: str = Field(default="#1a1a3e", pattern=r"^#[0-9a-fA-F]{6}$")
    blur: float = Field(default=0, ge=0, le=20)
    brightness: float = Field(default=100, ge=30, le=150)
    overlay: float = Field(default=40, ge=0, le=80)
    version: int = Field(default=0, ge=0)


class BackgroundPatch(BaseModel):
    targets: dict[Target, Background] = Field(default_factory=dict)
    surfaceTransparency: int | None = Field(default=None, ge=0, le=90)


class CopyBackground(BaseModel):
    source: Target
    targets: list[Target] = Field(min_length=1, max_length=4)


def configuration():
    saved = get_key("backgrounds", {})
    targets = {}
    for target in TARGETS:
        cfg = Background.model_validate(saved.get("targets", {}).get(target, {})).model_dump()
        # Discover images from older installations without a browser version counter.
        path = images._image_path(target)
        cfg["version"] = path.stat().st_mtime_ns // 1_000 if path.is_file() else 0
        if not saved and cfg["version"]:
            cfg["type"] = "image"
        targets[target] = cfg
    return {
        "targets": targets,
        "surfaceTransparency": saved.get("surfaceTransparency", 0),
        "configured": bool(saved),
    }


@router.get("/config")
async def get_configuration():
    # Public display metadata lets a fresh browser render the login background.
    # App photos still require authentication; login photos are intentionally public.
    return JSONResponse(configuration(), headers={"Cache-Control": "no-store"})


@router.put("/config")
async def update_configuration(body: BackgroundPatch, _: User = Depends(get_current_user)):
    async with _lock:
        config = configuration()
        for target, value in body.targets.items():
            config["targets"][target] = value.model_dump()
        if body.surfaceTransparency is not None:
            config["surfaceTransparency"] = body.surfaceTransparency
        set_key("backgrounds", config)
        return configuration()


async def decode(file: UploadFile):
    try:
        raw = await file.read(images.MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if len(raw) > images.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image too large — max 20 MB")
    try:
        return await asyncio.to_thread(images.compress_to_jpeg, raw)
    except Exception:
        raise HTTPException(400, "Invalid or unsupported image file")


def persist_image(config, target, data):
    images.save_image(target, data)
    config["targets"][target]["type"] = "image"
    config["targets"][target]["version"] = 0


@router.post("/apply")
async def apply_image(
    file: UploadFile,
    targets: Annotated[list[Target], Query(min_length=1, max_length=4)],
    _: User = Depends(get_current_user),
):
    compressed = await decode(file)
    async with _lock:
        config = configuration()
        for target in set(targets):
            persist_image(config, target, compressed)
        set_key("backgrounds", config)
        return configuration()


@router.post("/copy")
async def copy_background(body: CopyBackground, _: User = Depends(get_current_user)):
    async with _lock:
        config = configuration()
        source = config["targets"][body.source]
        data = images.load_image(body.source)
        if source["type"] == "image" and data is None:
            raise HTTPException(404, "Source image is not available")
        for target in set(body.targets):
            config["targets"][target] = dict(source)
            if data is not None:
                images.save_image(target, data)
            else:
                images.delete_image(target)
        set_key("backgrounds", config)
        return configuration()


@router.post("/{target}")
async def upload_background_image(
    target: Target, file: UploadFile, _: User = Depends(get_current_user)
):
    compressed = await decode(file)
    async with _lock:
        config = configuration()
        persist_image(config, target, compressed)
        set_key("backgrounds", config)
    return {"ok": True, "bytes": len(compressed)}


@router.delete("/{target}")
async def remove_background_image(target: Target, _: User = Depends(get_current_user)):
    async with _lock:
        images.delete_image(target)
        config = configuration()
        config["targets"][target]["type"] = "color"
        set_key("backgrounds", config)
    return {"ok": True}


def image_response(target):
    data = images.load_image(target)
    if data is None:
        raise HTTPException(404)
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


@router.get("/app")
async def get_app_background_image(_: User = Depends(get_current_user)):
    return image_response("app")


@router.get("/android-app")
async def get_android_app_background_image(_: User = Depends(get_current_user)):
    return image_response("android-app")


@router.get("/login")
async def get_login_background_image():
    return image_response("login")


@router.get("/android-login")
async def get_android_login_background_image():
    return image_response("android-login")
