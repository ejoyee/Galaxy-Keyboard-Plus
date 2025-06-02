def is_target_query(query: str) -> bool:
    """
    특정 질문인지 확인하는 함수
    "다음주 해운대 근처 성인 10명 묵을 수 있는 숙소 알려줘"와 유사한 질문을 감지
    """
    query_lower = query.lower().strip()

    # 키워드 조합으로 판단 (더 유연하게 확장)
    keywords = {
        "location": ["해운대", "부산", "haeundae"],
        "people": ["10명", "10인", "성인 10", "10 명", "십명", "10명", "10명 이상", "10인 이상", "10 명 이상", "10", "성인10", "어른 10"],
        "accommodation": ["숙소", "민박", "펜션", "호텔", "에어비앤비", "airbnb", "묵을", "머물", "숙박"],
        "request": ["알려줘", "추천", "찾아줘", "검색", "보여줘", "있는", "수 있는", "가능한"],
    }

    # 각 카테고리에서 최소 하나씩 포함되어야 함
    has_location = any(keyword in query_lower for keyword in keywords["location"])
    has_people = any(keyword in query_lower for keyword in keywords["people"])
    has_accommodation = any(
        keyword in query_lower for keyword in keywords["accommodation"]
    )
    has_request = any(keyword in query_lower for keyword in keywords["request"])

    # 디버깅을 위한 로그 추가
    logger.info(f"[is_target_query] 쿼리: {query}")
    logger.info(f"[is_target_query] 위치: {has_location}, 인원: {has_people}, 숙소: {has_accommodation}, 요청: {has_request}")

    return has_location and has_people and has_accommodation and has_request
