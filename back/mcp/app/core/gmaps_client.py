"""
Google Maps MCP 전용 클라이언트
- 서버 ID, URL, 헬퍼 메서드를 고정해 불필요한 if/else 제거
- 경로 요청 시 전체 구간 표시를 위한 로깅 및 검증 추가
"""

import aiohttp, uuid, logging
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)


class GoogleMapsMCPClient:
    def __init__(self, server_url: str = "http://localhost:8170/"):
        self.server_url = server_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

    # ────────────────────────────── life-cycle
    async def open(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    # ────────────────────────────── low-level call
    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session:
            raise RuntimeError("Session not initialised; call open() first.")
        async with self.session.post(
            self.server_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            return await resp.json()

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "call_tool",
            "params": {"name": name, "arguments": arguments},
        }
        log.debug("GMAPS call_tool » %s", payload)
        try:
            reply = await self._post(payload)
            log.debug("GMAPS result « %s", str(reply)[:200])
            
            # 경로 요청의 경우 응답 구조 검증 및 로깅
            if name == "maps_directions":
                self._validate_directions_response(reply, arguments)
            
            return reply.get("result", reply)
        except Exception as e:
            log.error("GMAPS MCP error: %s", e)
            return {"error": str(e)}

    def _validate_directions_response(self, response: Dict[str, Any], request_args: Dict[str, Any]):
        """경로 응답의 완전성을 검증하고 로깅"""
        try:
            result = response.get("result", {})
            if "routes" in result and len(result["routes"]) > 0:
                route = result["routes"][0]
                legs = route.get("legs", [])
                
                log.info(f"경로 요청 - 출발지: {request_args.get('origin')}, 도착지: {request_args.get('destination')}")
                log.info(f"경로 응답 - 총 구간 수: {len(legs)}")
                
                for i, leg in enumerate(legs):
                    start_address = leg.get("start_address", "알 수 없음")
                    end_address = leg.get("end_address", "알 수 없음")
                    steps_count = len(leg.get("steps", []))
                    log.info(f"구간 {i+1}: {start_address} → {end_address} (단계 수: {steps_count})")
                
                # 전체 경로가 올바르게 구성되었는지 확인
                if len(legs) == 0:
                    log.warning("⚠️ 경로 응답에 legs가 없습니다!")
                elif len(legs) == 1:
                    log.info("✅ 직접 경로 (1개 구간)")
                else:
                    log.info(f"✅ 다단계 경로 ({len(legs)}개 구간)")
            else:
                log.warning("⚠️ 경로 응답에 routes가 없거나 비어있습니다!")
        except Exception as e:
            log.error(f"경로 응답 검증 중 오류: {e}")

    # ────────────────────────────── helper wrappers
    async def geocode(self, address: str):
        return await self._call_tool("maps_geocode", {"address": address})

    async def reverse_geocode(self, lat: float, lon: float):
        return await self._call_tool(
            "maps_reverse_geocode", {"latitude": lat, "longitude": lon}
        )

    async def search_places(
        self,
        query: str,
        *,
        lat: float | None = None,
        lon: float | None = None,
        radius: int | None = None,
    ):
        args: Dict[str, Any] = {"query": query}
        if lat is not None and lon is not None:
            args["location"] = {"latitude": lat, "longitude": lon}
        if radius:
            args["radius"] = radius
        return await self._call_tool("maps_search_places", args)

    async def directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
    ):
        log.info(f"경로 요청: {origin} → {destination} (모드: {mode})")
        return await self._call_tool(
            "maps_directions",
            {"origin": origin, "destination": destination, "mode": mode},
        )