"""
Google Maps MCP 전용 클라이언트
- 서버 ID, URL, 헬퍼 메서드를 고정해 불필요한 if/else 제거
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
            return reply.get("result", reply)
        except Exception as e:
            log.error("GMAPS MCP error: %s", e)
            return {"error": str(e)}

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
        return await self._call_tool(
            "maps_directions",
            {"origin": origin, "destination": destination, "mode": mode},
        )
