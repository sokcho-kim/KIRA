"""
Meeting Routes
회의 녹음 및 관련 기능 라우트
"""

import logging
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.cc_slack_handlers import is_authorized_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meeting", tags=["meeting"])


def require_auth(request: Request) -> dict:
    """인증 확인"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/upload")
async def upload_recording(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(require_auth)
):
    """회의 녹음 파일 업로드"""
    try:
        # 파일 저장 로직
        contents = await file.read()
        file_path = f"/tmp/meeting_{file.filename}"

        with open(file_path, "wb") as f:
            f.write(contents)

        # 처리 로직 (STT, 요약 등)
        return JSONResponse({
            "status": "success",
            "message": f"Meeting recording {file.filename} uploaded",
            "user": user.get("name")
        })

    except Exception as e:
        logger.error(f"Failed to upload recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_recordings(request: Request, user: dict = Depends(require_auth)):
    """회의 녹음 목록 조회"""
    # 데이터베이스나 파일 시스템에서 목록 조회
    return {
        "recordings": [],
        "user": user.get("name")
    }


@router.get("/transcribe/{recording_id}")
async def get_transcription(
    recording_id: str,
    request: Request,
    user: dict = Depends(require_auth)
):
    """회의 녹음 전사 결과 조회"""
    # 전사 결과 반환
    return {
        "recording_id": recording_id,
        "transcription": "...",
        "user": user.get("name")
    }