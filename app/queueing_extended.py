import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

# 채널별 메시지 큐
message_queues: Dict[str, asyncio.Queue] = {}

# 글로벌 orchestrator 큐 (무거운 작업 전용)
orchestrator_queue = asyncio.Queue(maxsize=100)

# 메모리 저장 전용 큐 (순차 처리를 위한 단일 워커)
memory_queue = asyncio.Queue(maxsize=100)

# Orchestrator 워커 상태 관리
_active_orchestrator_workers = 0  # 현재 작업 중인 워커 수
_status_update_lock = asyncio.Lock()  # 상태 업데이트 중복 방지

# Debounce 관리를 위한 전역 변수들
_debounce_timers: Dict[str, asyncio.Task] = {}
_accumulated_messages: Dict[str, list] = {}


def get_or_create_channel_queue(channel_id: str) -> asyncio.Queue:
    """채널별 큐를 가져오거나 생성"""
    if channel_id not in message_queues:
        message_queues[channel_id] = asyncio.Queue(maxsize=100)
        logging.info(f"[QUEUE] Created new queue for channel: {channel_id}")
    return message_queues[channel_id]


async def enqueue_message(message):
    """채널별 메시지 큐에 추가"""
    channel_id = message.get("channel")
    queue = get_or_create_channel_queue(channel_id)
    await queue.put({"message": message})
    logging.info(f"[QUEUE] Message enqueued to channel {channel_id}, queue size: {queue.qsize()}")


async def enqueue_orchestrator_job(orchestrator_job: dict):
    """글로벌 orchestrator 큐에 작업 추가"""
    await orchestrator_queue.put(orchestrator_job)
    logging.info(f"[ORCHESTRATOR_QUEUE] Job enqueued, queue size: {orchestrator_queue.qsize()}")


async def enqueue_memory_job(memory_job: dict):
    """메모리 저장 큐에 작업 추가 (순차 처리)"""
    await memory_queue.put(memory_job)
    logging.info(f"[MEMORY_QUEUE] Job enqueued, queue size: {memory_queue.qsize()}")


async def debounced_enqueue_message(message, delay_seconds: float = 2.0):
    """Debounced version of enqueue_message - 지정된 시간간 추가 메시지가 없으면 누적된 메시지들을 합쳐서 처리

    Args:
        message: Slack 메시지 객체
        delay_seconds: debounce 지연 시간 (초), 0이면 즉시 처리
    """
    user_id = message.get("user")
    channel_id = message.get("channel")
    debounce_key = f"{channel_id}:{user_id}"

    # 0초면 즉시 처리
    if delay_seconds == 0:
        logging.info(f"[DEBOUNCE] Immediate processing for {user_id} in {channel_id} (delay=0)")
        await enqueue_message(message)
        return

    # 메시지 누적
    if debounce_key not in _accumulated_messages:
        _accumulated_messages[debounce_key] = []
        logging.info(f"[DEBOUNCE] First message from {user_id} in {channel_id}, starting {delay_seconds}s timer")
    else:
        logging.info(f"[DEBOUNCE] Additional message from {user_id} in {channel_id}, resetting timer")

    _accumulated_messages[debounce_key].append({
        "message": message,
        "timestamp": datetime.now()
    })

    # 기존 타이머가 있다면 취소
    if debounce_key in _debounce_timers:
        _debounce_timers[debounce_key].cancel()
        logging.info(f"[DEBOUNCE] Cancelled previous timer for {debounce_key}")

    # 새 타이머 시작
    async def delayed_process():
        try:
            await asyncio.sleep(delay_seconds)

            # 타이머 만료 후 누적된 메시지들을 합쳐서 처리
            if debounce_key in _accumulated_messages:
                accumulated = _accumulated_messages[debounce_key]
                message_count = len(accumulated)
                logging.info(f"[DEBOUNCE] Timer expired, merging {message_count} messages from {user_id} in {channel_id}")

                # 메시지들의 텍스트를 합치기
                merged_text_parts = []
                base_message = accumulated[0]["message"].copy()  # 첫 번째 메시지를 베이스로 사용

                for msg_data in accumulated:
                    msg = msg_data["message"]
                    text = msg.get("text", "").strip()
                    if text:
                        merged_text_parts.append(text)

                # 합친 텍스트로 메시지 생성
                if merged_text_parts:
                    base_message["text"] = "\n".join(merged_text_parts)
                    logging.info(f"[DEBOUNCE] Merged text: {base_message['text'][:100]}...")

                    # 실제 메시지 처리
                    await enqueue_message(base_message)
                else:
                    logging.warning(f"[DEBOUNCE] No text content found in {message_count} messages")

                # 정리
                del _accumulated_messages[debounce_key]
                if debounce_key in _debounce_timers:
                    del _debounce_timers[debounce_key]

        except asyncio.CancelledError:
            logging.info(f"[DEBOUNCE] Timer cancelled for {debounce_key}")
            raise
        except Exception as e:
            logging.error(f"[DEBOUNCE] Error in delayed processing for {debounce_key}: {e}")
            # 에러 발생시에도 정리
            if debounce_key in _accumulated_messages:
                del _accumulated_messages[debounce_key]
            if debounce_key in _debounce_timers:
                del _debounce_timers[debounce_key]

    # 새 타이머 등록
    _debounce_timers[debounce_key] = asyncio.create_task(delayed_process())


def start_channel_workers(app, process_func, workers_per_channel=5):
    """채널별 worker 시작 - 각 채널의 메시지를 병렬 처리"""

    async def channel_worker(channel_id: str, queue: asyncio.Queue, worker_id: int):
        """특정 채널의 메시지를 병렬 처리하는 worker"""
        client = app.client
        logging.info(f"[CHANNEL_WORKER-{worker_id}] Started worker for channel: {channel_id}")

        while True:
            try:
                job = await queue.get()
                message = job["message"]

                logging.info(f"[CHANNEL_WORKER-{worker_id}] Processing message in {channel_id}, queue size: {queue.qsize()}")
                await process_func(message, client)

            except Exception as e:
                logging.error(f"[CHANNEL_WORKER-{worker_id}] Error in channel {channel_id}: {e}")
            finally:
                queue.task_done()

    async def monitor_and_spawn_workers():
        """새로운 채널 큐가 생성되면 자동으로 worker 생성"""
        monitored_channels = set()

        while True:
            await asyncio.sleep(1)  # 1초마다 체크

            for channel_id, queue in list(message_queues.items()):
                if channel_id not in monitored_channels:
                    # 새 채널 발견, 채널당 여러 worker 생성
                    for worker_id in range(workers_per_channel):
                        asyncio.create_task(channel_worker(channel_id, queue, worker_id))
                    monitored_channels.add(channel_id)
                    logging.info(f"[MONITOR] Spawned {workers_per_channel} workers for new channel: {channel_id}")

    loop = asyncio.get_running_loop()
    loop.create_task(monitor_and_spawn_workers())


def start_orchestrator_worker(app, orchestrator_func, num_workers=2):
    """글로벌 orchestrator worker 시작 - 모든 orchestrator 작업을 병렬 처리"""

    async def orchestrator_worker(worker_id: int):
        global _active_orchestrator_workers
        client = app.client
        logging.info(f"[ORCHESTRATOR_WORKER-{worker_id}] Started")

        # 봇 상태 업데이트 함수
        async def update_bot_status():
            global _active_orchestrator_workers

            # Lock을 사용해서 동시 업데이트 방지
            async with _status_update_lock:
                active_workers = _active_orchestrator_workers
                is_busy = active_workers >= num_workers  # 모든 워커가 작업 중이면 busy

                logging.info(f"[STATUS] Updating bot status (active_workers: {active_workers}/{num_workers}, is_busy: {is_busy})")
                try:
                    if is_busy:
                        await client.users_profile_set(
                            profile={
                                "status_text": "i'm busy",
                                "status_emoji": ":hourglass_flowing_sand:"
                            }
                        )
                        logging.info(f"[STATUS] Bot status updated to BUSY")
                    else:
                        await client.users_profile_set(
                            profile={
                                "status_text": "",
                                "status_emoji": "",
                                "status_expiration": 0
                            }
                        )
                        logging.info(f"[STATUS] Bot status cleared")
                except Exception as e:
                    if "not_allowed_token_type" in str(e):
                        logging.debug(f"[STATUS] Bot status update not supported with current token type")
                    else:
                        logging.warning(f"[STATUS] Failed to update bot status: {e}")

        while True:
            logging.info(f"[ORCHESTRATOR_WORKER-{worker_id}] Waiting for next job from queue...")
            job = await orchestrator_queue.get()
            logging.info(f"[ORCHESTRATOR_WORKER-{worker_id}] Job received from queue")

            try:
                # 작업 시작 - active worker 증가
                _active_orchestrator_workers += 1
                logging.info(f"[ORCHESTRATOR_WORKER-{worker_id}] Started job (active: {_active_orchestrator_workers}/{num_workers})")
                await update_bot_status()

                await orchestrator_func(job, client)
                logging.info(f"[ORCHESTRATOR_WORKER-{worker_id}] Job completed successfully")
            except Exception as e:
                logging.error(f"[ORCHESTRATOR_WORKER-{worker_id}] Error: {e}")
            finally:
                # 작업 완료 - active worker 감소
                _active_orchestrator_workers -= 1
                orchestrator_queue.task_done()
                logging.info(f"[ORCHESTRATOR_WORKER-{worker_id}] Finished job (active: {_active_orchestrator_workers}/{num_workers})")
                await update_bot_status()

    loop = asyncio.get_running_loop()
    for worker_id in range(num_workers):
        loop.create_task(orchestrator_worker(worker_id))
        logging.info(f"[ORCHESTRATOR_WORKER] Created worker {worker_id}/{num_workers}")


def start_memory_worker(memory_func):
    """메모리 저장 전용 워커 시작 (단일 워커로 순차 처리)

    Args:
        memory_func: 메모리 저장 함수 (job dict를 받아 처리)
    """
    async def memory_worker():
        logging.info(f"[MEMORY_WORKER] Started")

        while True:
            logging.info(f"[MEMORY_WORKER] Waiting for next job...")
            job = await memory_queue.get()
            logging.info(f"[MEMORY_WORKER] Job received from queue (queue size: {memory_queue.qsize()})")

            try:
                await memory_func(job)
                logging.info(f"[MEMORY_WORKER] Job completed successfully")
            except Exception as e:
                logging.error(f"[MEMORY_WORKER] Error: {e}")
            finally:
                memory_queue.task_done()

    loop = asyncio.get_running_loop()
    loop.create_task(memory_worker())
    logging.info(f"[MEMORY_WORKER] Created single worker for sequential memory operations")