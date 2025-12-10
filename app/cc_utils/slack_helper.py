"""
Slack API Helper Functions
채널 정보, 사용자 정보 등을 조회하는 유틸리티 함수
"""

from typing import Dict, Any, Optional, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

# 봇 프로필 이미지 캐시
_bot_profile_image: Optional[str] = None


def get_slack_client() -> WebClient:
    """Slack WebClient 인스턴스 반환"""
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is not set")
    return WebClient(token=token)


def get_channel_info(channel_id: str) -> Optional[Dict[str, Any]]:
    """
    채널 정보 조회

    Args:
        channel_id: Slack 채널 ID

    Returns:
        {
            "channel_id": str,
            "channel_name": str,
            "channel_type": str,  # "public_channel", "private_channel", "im", "mpim"
            "is_private": bool,
            "topic": str,
            "purpose": str,
            "member_count": int,
            "members": List[str]  # 채널 멤버 ID 리스트
        }
    """
    client = get_slack_client()

    try:
        # 채널 정보 조회
        response = client.conversations_info(channel=channel_id)
        channel = response["channel"]

        # 채널 타입 결정
        if channel.get("is_im"):
            channel_type = "dm"
        elif channel.get("is_mpim"):
            channel_type = "group_dm"
        elif channel.get("is_private"):
            channel_type = "private_channel"
        else:
            channel_type = "public_channel"

        # 채널 멤버 조회 (DM이 아닌 경우)
        members = []
        if not channel.get("is_im"):
            try:
                members_response = client.conversations_members(channel=channel_id)
                members = members_response["members"]
            except SlackApiError as e:
                print(f"Failed to get channel members: {e}")

        return {
            "channel_id": channel["id"],
            "channel_name": channel.get("name", "Direct Message"),
            "channel_type": channel_type,
            "is_private": channel.get("is_private", False),
            "topic": channel.get("topic", {}).get("value", ""),
            "purpose": channel.get("purpose", {}).get("value", ""),
            "member_count": channel.get("num_members", len(members)),
            "members": members
        }

    except SlackApiError as e:
        print(f"Error fetching channel info: {e}")
        return None


def get_bot_profile_image() -> str:
    """
    슬랙 봇의 프로필 이미지 URL을 가져옵니다.

    Returns:
        봇의 프로필 이미지 URL (512x512)
    """
    global _bot_profile_image

    # 캐시된 값이 있으면 반환
    if _bot_profile_image:
        return _bot_profile_image

    client = get_slack_client()

    try:
        # 봇 정보 가져오기
        auth_response = client.auth_test()
        bot_user_id = auth_response.get('user_id')

        # 봇 프로필 이미지 가져오기
        user_info = client.users_info(user=bot_user_id)
        _bot_profile_image = user_info.get('user', {}).get('profile', {}).get('image_512', '')

        print(f"[SLACK] Bot profile image loaded: {bot_user_id}")
        return _bot_profile_image
    except SlackApiError as e:
        print(f"[SLACK] Failed to get bot profile image: {e}")
        # fallback 이미지
        return "https://ca.slack-edge.com/E01DL1Z9D6Z-U09EV9ED4HL-68cc5ad19dd2-512"


def get_user_info(user_id: str) -> Optional[Dict[str, Any]]:
    """
    사용자 정보 조회

    Args:
        user_id: Slack 사용자 ID

    Returns:
        {
            "user_id": str,
            "real_name": str,
            "display_name": str,
            "email": str,
            "is_bot": bool,
            "timezone": str
        }
    """
    client = get_slack_client()

    try:
        response = client.users_info(user=user_id)
        user = response["user"]

        return {
            "user_id": user["id"],
            "real_name": user.get("real_name", ""),
            "display_name": user.get("profile", {}).get("display_name", ""),
            "email": user.get("profile", {}).get("email", ""),
            "is_bot": user.get("is_bot", False),
            "timezone": user.get("tz", "")
        }

    except SlackApiError as e:
        print(f"Error fetching user info: {e}")
        return None


def get_channel_members_info(channel_id: str) -> List[Dict[str, Any]]:
    """
    채널 멤버들의 상세 정보 조회

    Args:
        channel_id: Slack 채널 ID

    Returns:
        List of user info dicts
    """
    channel_info = get_channel_info(channel_id)
    if not channel_info:
        return []

    members = channel_info.get("members", [])
    members_info = []

    for user_id in members:
        user_info = get_user_info(user_id)
        if user_info and not user_info["is_bot"]:  # 봇 제외
            members_info.append(user_info)

    return members_info


def get_thread_messages(channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
    """
    스레드의 모든 메시지 조회

    Args:
        channel_id: Slack 채널 ID
        thread_ts: 스레드 타임스탬프

    Returns:
        List of message dicts
    """
    client = get_slack_client()

    try:
        response = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts
        )
        return response["messages"]

    except SlackApiError as e:
        print(f"Error fetching thread messages: {e}")
        return []


def get_recent_messages(channel_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    채널의 최근 메시지 조회

    Args:
        channel_id: Slack 채널 ID
        limit: 조회할 메시지 개수 (기본 100개)

    Returns:
        List of message dicts (최신순)
    """
    client = get_slack_client()

    try:
        response = client.conversations_history(
            channel=channel_id,
            limit=limit
        )
        return response["messages"]

    except SlackApiError as e:
        print(f"Error fetching recent messages: {e}")
        return []


def format_message_for_context(message: Dict[str, Any]) -> str:
    """
    Slack 메시지를 Context 저장용으로 포맷팅

    Args:
        message: Slack 메시지 딕셔너리

    Returns:
        포맷팅된 메시지 문자열 (예: "[사용자명]: 메시지 내용")
    """
    # 사용자 정보 조회
    user_id = message.get("user")
    if user_id:
        user_info = get_user_info(user_id)
        user_name = user_info["real_name"] if user_info else user_id
    elif message.get("bot_id"):
        user_name = "Bot"
    else:
        user_name = "Unknown"

    text = message.get("text", "")

    return f"[{user_name}]: {text}"


def get_conversation_history_for_context(
    channel_id: str,
    limit: int = 10
) -> List[str]:
    """
    ChannelContext 저장용 대화 히스토리 생성

    Args:
        channel_id: Slack 채널 ID
        limit: 조회할 메시지 개수

    Returns:
        포맷팅된 대화 내역 리스트 (오래된 순서)
    """
    messages = get_recent_messages(channel_id, limit)

    # 오래된 순서로 정렬 (messages는 최신순으로 반환됨)
    messages.reverse()

    formatted_messages = []
    for msg in messages:
        formatted = format_message_for_context(msg)
        formatted_messages.append(formatted)

    return formatted_messages


def get_slack_context_data(channel_id: str, message_limit: int = 10) -> Dict[str, Any]:
    """
    Orchestrator에게 제공할 Slack 데이터를 모두 모아서 반환

    Args:
        channel_id: Slack 채널 ID
        message_limit: 조회할 최근 메시지 개수 (기본 10개)

    Returns:
        {
            "channel": {
                "channel_id": str,
                "channel_name": str,
                "channel_type": str,
                "topic": str,
                "purpose": str,
                "member_count": int
            },
            "members": [
                {
                    "user_id": str,
                    "real_name": str,
                    "display_name": str,
                    "email": str
                },
                ...
            ],
            "recent_messages": [
                "[사용자명]: 메시지 내용",
                ...
            ]
        }
    """
    # 채널 정보 조회
    channel_info = get_channel_info(channel_id)
    if not channel_info:
        return {
            "channel": {
                "channel_id": channel_id,
                "channel_name": "Unknown",
                "channel_type": "unknown",
                "topic": "",
                "purpose": "",
                "member_count": 0
            },
            "members": [],
            "recent_messages": []
        }

    # 멤버 정보 조회 (봇 제외)
    members_info = get_channel_members_info(channel_id)

    # 최근 대화 내역 조회
    conversation_history = get_conversation_history_for_context(channel_id, message_limit)

    return {
        "channel": {
            "channel_id": channel_info["channel_id"],
            "channel_name": channel_info["channel_name"],
            "channel_type": channel_info["channel_type"],
            "topic": channel_info["topic"],
            "purpose": channel_info["purpose"],
            "member_count": channel_info["member_count"]
        },
        "members": [
            {
                "user_id": m["user_id"],
                "real_name": m["real_name"],
                "display_name": m["display_name"],
                "email": m["email"]
            }
            for m in members_info
        ],
        "recent_messages": conversation_history
    }


