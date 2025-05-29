from fastapi import APIRouter, Query

router = APIRouter()

# 키워드 사전 정의
TASK_KEYWORDS = {
    "maps": {"거리", "지도", "위치", "맛집", "주변", "길", "소요시간", "근처"},
    "opencv": {"사진", "이미지", "크롭", "자르기", "보정", "화질", "얼굴", "편집"},
    "gmail": {"지메일", "gmail", "메일", "전송", "받은편지함"},
    "calendar": {"캘린더", "일정", "등록", "추가", "스케줄"},
}


@router.get("/mcp/match/")
def match_task_by_word(word: str = Query(..., description="사용자의 단어 입력")):
    """
    단어 하나를 받아 어떤 작업(maps, opencv, gmail, calendar)에 해당하는지 판별합니다.
    일치하는 작업이 없으면 'none' 반환
    """

    word = word.strip().lower()

    for task, keywords in TASK_KEYWORDS.items():
        if word in keywords:
            return {"word": word, "matched_task": task}

    return {"word": word, "matched_task": "none"}
