from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import asyncio
import logging

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    summary="MCP 서버 상태 확인",
    description="모든 MCP 서버의 현재 상태 정보 반환"
)
async def get_server_status(request: Request) -> Dict[str, Any]:
    """MCP 서버 상태 정보 반환"""
    if not hasattr(request.app.state, "mcp_manager"):
        logger.error("MCP manager not initialized")
        raise HTTPException(status_code=503, detail="MCP manager not initialized")
    
    mcp_manager = request.app.state.mcp_manager
    server_status = {}
    
    # 서버 상태 수집
    for name, server in mcp_manager.servers.items():
        is_running = server is not None and server.returncode is None
        client_connected = name in mcp_manager.clients
        
        server_status[name] = {
            "name": name,
            "status": "running" if is_running else "stopped",
            "port": mcp_manager.web_search_port if name == "web_search" else None,
            "client_connected": client_connected
        }
        
        logger.info(f"Server {name} status: {'running' if is_running else 'stopped'}, client connected: {client_connected}")
    
    # 현재 서버 목록이 비어있다면 web_search 서버를 강제로 등록
    if len(server_status) == 0:
        logger.warning("No servers found, registering web_search server explicitly")
        server_status["web_search"] = {
            "name": "web_search",
            "status": "stopped",
            "port": mcp_manager.web_search_port,
            "client_connected": False
        }
    
    return {
        "servers": server_status,
        "total_count": len(server_status)
    }