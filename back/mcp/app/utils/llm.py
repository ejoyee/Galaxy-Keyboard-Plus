import os
import json
import logging
from openai import OpenAI
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 로그 초기화
logger = logging.getLogger(__name__)

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_tools_for_openai(tools_info):
    tool_list = []
    for srv, tools in tools_info.items():
        for tool in tools:
            tool_list.append(
                {
                    "type": "function",
                    "function": {
                        # 반드시 MCP 서버명_툴명으로 이름 생성!
                        "name": f"{srv}_{tool['name']}",
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", {}),
                    },
                }
            )
    return tool_list
    # [
    #   {"type": "function", "function": {"name": "brave_brave_web_search", ...}},
    #   {"type": "function", "function": {"name": "brave_brave_local_search", ...}}
    # ]


async def call_llm(query: str, tools_info: dict, settings=None) -> dict:

    # tools_info: {"brave": [tool, tool, ...], ...}
    tools = format_tools_for_openai(tools_info)

    system_prompt = """
    You are a specialized agent that transforms user requests into calls to the registered MCP tools, or else returns plain-text answers.

    Guidelines:
    1. TOOL CALL
        • If a request requires tool access (web search, etc.), emit exactly one tool call JSON with the correct tool name and all required parameters.
        • Use only the provided tool names and schemas—do not invent new tools or free-form code.
    2. TEXT RESPONSE
        • If the request can be satisfied without a tool call, reply with natural-language text and do not call any tool.
    3. FOLLOW-UP QUESTIONS
        • If a required parameter is missing or ambiguous, ask the user a clarifying question instead of guessing.
    4. NO EXTRA VERBIAGE
        • When calling a tool, respond with strictly the function call object—no explanatory text.
        • Any human-readable explanation should only appear in plain-text responses when no tool is invoked.
    """
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        tools=tools,
        tool_choice="auto",
        max_tokens=1024,
    )

    """
    "message": {
        "roe": "assistant",
            "content": "2024년 인공지능의 최신 동향은 다음과 같습니다: ...",
        // tool_calls 없음!
    }
    "message": {
        "role": "assistant",
        "content": null,  // 텍스트 답변은 없음
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "brave_web_search",
              "arguments": "{\"query\": \"인공지능 최신 동향\", \"limit\": 5}"
            }
          }
        ]
    }
    """

    msg = response.choices[0].message

    # ----- 1. tool_calls 파싱 -----
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls and isinstance(tool_calls, list) and tool_calls:
        fc = tool_calls[0].function
    else:
        fc = None

    # ----- 2. 툴 호출 없으면 텍스트 응답 -----
    if not fc or not hasattr(fc, "arguments"):
        return {"type": "text", "content": msg.content or ""}

    # ----- 3. arguments JSON 파싱 -----
    try:
        arguments = fc.arguments
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except Exception:
        logger.error(
            f"Failed to parse tool arguments: {getattr(fc, 'arguments', None)}"
        )
        return {"type": "text", "content": msg.content or ""}

    params = parsed.get("params", parsed)

    # ----- 4. tool name에서 서버명/툴명 추출 -----
    alias = fc.name
    try:
        srvId, method = alias.split("_", 1)
    except Exception:
        logger.error(f"Invalid tool alias format: {alias}")
        return {"type": "text", "content": msg.content or ""}

    # ----- 5. 최종 결과 반환 -----
    return {
        "type": "rpc",
        "srvId": srvId,
        "method": method,
        "params": params,
    }


async def summarize_with_llm(rpc_result: dict, prompt: str = "", settings=None) -> dict:
    """
    MCP 툴 호출 결과를 OpenAI로 한글 자연어 요약
    - rpc_result: MCP 서버에서 받은 raw 결과 (dict)
    - prompt: 원래 사용자의 질문 (optional, 있으면 더 자연스럽게 요약 가능)
    """

    # 1. rawResult 추출
    #   - rpc_result["content"]가 list면 type=text 인 것만 골라 text를 이어붙임
    #   - 아니면 그냥 전체를 json으로 직렬화
    if isinstance(rpc_result, dict) and isinstance(rpc_result.get("content"), list):
        rawResult = "\n".join(
            c.get("text", "") for c in rpc_result["content"] if c.get("type") == "text"
        )
    else:
        rawResult = json.dumps(rpc_result, ensure_ascii=False, indent=2)

    # 2. 요약용 system/user/assistant 프롬프트 구성
    system_prompt = (
        "You are a helpful assistant. The user made a request, "
        "we ran a filesystem tool and got some raw output. "
        "Now produce a single, concise, natural-language response "
        "that explains the result to the user. "
        "답변은 한글로 해주세요."
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if prompt:
        messages.append({"role": "user", "content": f"Original request:\n{prompt}"})
    messages.append({"role": "assistant", "content": f"Tool output:\n{rawResult}"})

    # 3. OpenAI 요약 호출
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1024,
        temperature=0.4,
    )
    friendly = response.choices[0].message.content.strip()

    # 4. 반환
    return {"results": [{"description": friendly}]}


import re


async def call_llm_for_airbnb(query: str) -> dict:
    """
    Airbnb 자연어 쿼리를 MCP 툴 호출 포맷으로 변환
    """
    system_prompt = """
    사용자의 숙소 검색 요청을 분석해서 MCP 툴 호출 JSON으로 변환하세요.

    조건:
    - MCP 서버: airbnb-mcp
    - 툴 이름: airbnb_search
    - 반환 형식 예시:
    {
        "type": "rpc",
        "srvId": "airbnb-mcp",
        "method": "airbnb_search",
        "params": {
            "location": "부산",
            "checkin": "2025-05-30",
            "checkout": "2025-06-01",
            "adults": 2
        }
    }
    - 날짜, 인원수, 위치는 자연어로 입력되더라도 가능한 정확히 추론하세요.
    - 정보가 부족한 경우 기본값을 쓰되, 명확하지 않으면 tool 호출 없이 자연어로 답하세요.
    - 한글로 된 자연어 요청을 이해하세요.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1024,
        temperature=0.2,
    )

    msg = response.choices[0].message
    content = msg.content.strip()

    # 코드블럭 안의 JSON 추출 시도
    try:
        # 1. 코드 블록 안 JSON 추출
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            raw_json = json_match.group(1)
            result = json.loads(raw_json)
        else:
            # 2. 코드 블록 없이 직접 JSON 응답
            result = json.loads(content)

        # 3. ✅ srvId 정정
        if result.get("type") == "rpc":
            result["srvId"] = "airbnb"

        return result

    except Exception:
        logger.warning("🔴 Airbnb 전용 LLM 호출 결과 파싱 실패")
        return {"type": "text", "content": content or "답변을 이해하지 못했어요."}
