"""
KIRA Web Interface Server
음성 입력 및 웹 인터페이스 서버
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# 라우터 임포트
from app.cc_web_interface.routes import (
    auth_router,
    bot_auth_router,
    meeting_router,
    voice_router,
    api_router
)
from app.cc_web_interface.auth_handler import auth_handler
from app.cc_web_interface.utils import get_session_user, require_auth
from app.cc_slack_handlers import is_authorized_user
from app.cc_utils.slack_helper import get_bot_profile_image

logger = logging.getLogger(__name__)

# FastAPI 앱 생성
web_app = FastAPI(title="KIRA Web Interface")

# 세션 미들웨어 추가
web_app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-change-this-in-production"  # TODO: 환경변수로 변경
)

# 정적 파일 서빙
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    web_app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 라우터 등록
web_app.include_router(auth_router)
web_app.include_router(bot_auth_router)
web_app.include_router(meeting_router)
web_app.include_router(voice_router)
web_app.include_router(api_router)


@web_app.get("/")
async def home(request: Request):
    """메인 페이지 (음성 입력 UI)"""
    # 로그인 체크
    user = get_session_user(request)

    if not user:
        # 로그인 필요하면 로그인 페이지로
        if require_auth(request):
            return await auth_handler.handle_login(request)
        else:
            # 개발 모드 - 가상 사용자 설정
            user = {
                'email': 'dev@localhost',
                'name': 'Developer',
                'id': 'dev_user'
            }
            request.session['user'] = user

    # 인가된 사용자인지 재확인
    if not is_authorized_user(user.get('name', '')):
        logger.warning(f"[AUTH] Unauthorized access attempt: {user.get('name')} ({user.get('email')})")
        request.session.clear()
        return HTMLResponse(
            content=f"<h1>접근 권한이 없습니다</h1><p>사용자: {user.get('name')} ({user.get('email')})</p><p>관리자에게 문의하세요.</p>",
            status_code=403
        )

    # 로그인된 사용자: 음성 UI 표시
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 템플릿 변수 치환
        from app.config.settings import get_settings
        settings = get_settings()
        bot_profile_image = get_bot_profile_image()

        html_content = html_content.replace('{{BOT_NAME}}', settings.BOT_NAME)
        html_content = html_content.replace('{{BOT_ORGANIZATION}}', settings.BOT_ORGANIZATION)
        html_content = html_content.replace('{{USER_NAME}}', user.get('name', '사용자'))
        html_content = html_content.replace('{{BOT_PROFILE_IMAGE}}', bot_profile_image)
        html_content = html_content.replace('{{CLOVA_ENABLED}}', str(settings.CLOVA_ENABLED).lower())

        return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="<h1>음성 인터페이스</h1><p>index.html 파일이 없습니다.</p>")


@web_app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "KIRA Web Interface"}