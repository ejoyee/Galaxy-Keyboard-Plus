from datetime import datetime


def parse_address_keywords(address: str) -> list[str]:
    """
    주소 문자열을 기반으로 주요 지역 단어 키워드 추출
    예: "대한민국 서울특별시 강남구 역삼동" → ["대한민국", "서울", "강남구", "역삼동"]
    """
    if not address:
        return []

    return [word.strip() for word in address.split() if word.strip()]


def parse_time_keywords(image_time_str: str) -> list[str]:
    """
    EXIF 시각 문자열 기반 키워드 생성
    예: "2025:05:15 14:20:00" → ["2025년", "05월", "15일", "오후"]
    """
    try:
        dt = datetime.strptime(image_time_str, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return []

    keywords = [dt.strftime("%Y년"), dt.strftime("%m월"), dt.strftime("%d일")]

    hour = dt.hour
    if 5 <= hour < 12:
        keywords.append("오전")
    elif 12 <= hour < 18:
        keywords.append("오후")
    else:
        keywords.append("야간")

    return keywords
