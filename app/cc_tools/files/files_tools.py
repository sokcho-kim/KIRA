"""
Files Tools for Claude Code SDK
파일 저장/변환 관련 도구
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict

from claude_agent_sdk import create_sdk_mcp_server, tool

from app.config.settings import get_settings


def get_base_dir() -> Path:
    """파일 저장 기본 디렉토리 반환"""
    settings = get_settings()
    base_dir = settings.FILESYSTEM_BASE_DIR
    if not base_dir:
        base_dir = os.path.expanduser("~/Documents/KIRA")
    return Path(base_dir)


@tool(
    "save_base64_image",
    "base64로 인코딩된 이미지 데이터를 파일로 저장합니다. Tableau 등에서 받은 이미지를 저장할 때 사용하세요.",
    {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "저장할 파일 경로 (예: files/C12345/dashboard.png). FILESYSTEM_BASE_DIR 기준 상대경로 또는 절대경로"
            },
            "base64_data": {
                "type": "string",
                "description": "base64로 인코딩된 이미지 데이터 (data:image/png;base64, 접두사 있어도 됨)"
            }
        },
        "required": ["file_path", "base64_data"]
    }
)
async def save_base64_image(args: Dict[str, Any]) -> Dict[str, Any]:
    """base64 이미지를 파일로 저장"""
    file_path = args["file_path"]
    base64_data = args["base64_data"]

    try:
        # data:image/png;base64, 접두사 제거
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]

        # base64 디코딩
        image_data = base64.b64decode(base64_data)

        # 경로 처리
        if not os.path.isabs(file_path):
            full_path = get_base_dir() / file_path
        else:
            full_path = Path(file_path)

        # 디렉토리 생성
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 파일 저장
        with open(full_path, "wb") as f:
            f.write(image_data)

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "message": f"이미지 저장 완료",
                    "path": str(full_path),
                    "size_bytes": len(image_data)
                }, ensure_ascii=False, indent=2)
            }]
        }

    except base64.binascii.Error as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": f"base64 디코딩 실패: {str(e)}"
                }, ensure_ascii=False, indent=2)
            }],
            "isError": True
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": f"파일 저장 실패: {str(e)}"
                }, ensure_ascii=False, indent=2)
            }],
            "isError": True
        }


@tool(
    "read_file_as_base64",
    "파일을 읽어서 base64로 인코딩합니다. 이미지 파일을 Slack에 업로드하기 전 등에 사용하세요.",
    {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "읽을 파일 경로. FILESYSTEM_BASE_DIR 기준 상대경로 또는 절대경로"
            }
        },
        "required": ["file_path"]
    }
)
async def read_file_as_base64(args: Dict[str, Any]) -> Dict[str, Any]:
    """파일을 base64로 읽기"""
    file_path = args["file_path"]

    try:
        # 경로 처리
        if not os.path.isabs(file_path):
            full_path = get_base_dir() / file_path
        else:
            full_path = Path(file_path)

        if not full_path.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "success": False,
                        "error": f"파일을 찾을 수 없습니다: {full_path}"
                    }, ensure_ascii=False, indent=2)
                }],
                "isError": True
            }

        # 파일 읽기 및 base64 인코딩
        with open(full_path, "rb") as f:
            file_data = f.read()

        base64_data = base64.b64encode(file_data).decode("utf-8")

        # MIME 타입 추정
        suffix = full_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
        }
        mime_type = mime_types.get(suffix, "application/octet-stream")

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "path": str(full_path),
                    "size_bytes": len(file_data),
                    "mime_type": mime_type,
                    "base64_data": base64_data
                }, ensure_ascii=False, indent=2)
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "success": False,
                    "error": f"파일 읽기 실패: {str(e)}"
                }, ensure_ascii=False, indent=2)
            }],
            "isError": True
        }


# 도구 등록
files_tools = [save_base64_image, read_file_as_base64]


def create_files_mcp_server():
    """Claude Code SDK Files MCP server"""
    return create_sdk_mcp_server(name="files-tools", version="1.0.0", tools=files_tools)
