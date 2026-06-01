"""KIS 실시간 WebSocket 클라이언트.

연결 → 구독메시지 송신 → 프레임 수신(async iterator) → PINGPONG 응답.
연결 끊기면 백오프 재연결 후 현재 구독을 자동 재등록.
실시간 데이터(0/1로 시작)는 호출측에 그대로 yield, 시스템 메시지(JSON)는 내부 처리.
"""
from __future__ import annotations
import asyncio
import json
import logging
from collections.abc import AsyncIterator

import websockets

logger = logging.getLogger(__name__)


def build_sub_message(approval_key: str, tr_id: str, tr_key: str,
                      register: bool = True) -> str:
    return json.dumps({
        "header": {"approval_key": approval_key, "custtype": "P",
                   "tr_type": "1" if register else "2", "content-type": "utf-8"},
        "body": {"input": {"tr_id": tr_id, "tr_key": tr_key}},
    })


class KISWebSocket:
    def __init__(self, ws_url: str, approval_key: str):
        self._url = ws_url
        self._approval = approval_key
        self._ws = None
        self._subs: set[tuple[str, str]] = set()   # (tr_id, symbol)

    async def connect(self) -> None:
        self._ws = await websockets.connect(self._url, ping_interval=None)
        # 재연결이면 기존 구독 복원
        for tr_id, sym in list(self._subs):
            await self._ws.send(build_sub_message(self._approval, tr_id, sym, True))
        logger.info("WS connected: %s (resubscribed %d)", self._url, len(self._subs))

    async def register(self, tr_id: str, symbol: str) -> None:
        self._subs.add((tr_id, symbol))
        await self._ws.send(build_sub_message(self._approval, tr_id, symbol, True))

    async def unregister(self, tr_id: str, symbol: str) -> None:
        self._subs.discard((tr_id, symbol))
        await self._ws.send(build_sub_message(self._approval, tr_id, symbol, False))

    async def frames(self) -> AsyncIterator[str]:
        """실시간 데이터 프레임만 yield. PINGPONG은 자동 응답. 끊기면 재연결."""
        while True:
            try:
                raw = await self._ws.recv()
            except websockets.ConnectionClosed:
                logger.warning("WS closed, reconnecting...")
                await self._reconnect()
                continue
            if raw and raw[0] in ("0", "1"):
                yield raw
            else:
                # 시스템 메시지: PINGPONG이면 받은 텍스트를 그대로 echo (앱 레벨 keepalive)
                try:
                    if json.loads(raw)["header"]["tr_id"] == "PINGPONG":
                        await self._ws.send(raw)
                except (json.JSONDecodeError, KeyError):
                    pass

    async def _reconnect(self) -> None:
        delay = 1
        while True:
            try:
                await self.connect()
                return
            except Exception as e:               # noqa: BLE001 - 재연결은 모든 예외 재시도
                logger.warning("reconnect failed (%s), retry in %ds", e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
