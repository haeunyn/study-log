"""form_errors.py — Pydantic 검증 실패를 화면용 한국어 메시지로 바꾼다. (보너스 2)

■ 왜 필요한가?
  Pydantic 이 주는 기본 메시지는 영어이고 개발자용이다.
  예: "String should have at least 2 characters"
  사용자에게는 "제목은 2글자 이상 입력해 주세요." 가 필요하다.

■ 왜 이 변환을 서비스가 아니라 여기서 하는가?
  이것은 '화면에 어떻게 보여줄까'의 문제이지 업무 규칙이 아니다.
  규칙(2글자 이상)은 schemas 에 있고, 그 규칙을 사람 말로 옮기는 것만 여기서 한다.
"""

from pydantic import ValidationError

# 필드 이름 → 화면에 보여줄 한국어 이름
FIELD_NAMES: dict[str, str] = {
    "title": "제목",
    "content": "내용",
    "studied_on": "학습일",
    "minutes": "학습 시간",
    "category": "분야",
}


def to_korean_errors(exc: ValidationError) -> dict[str, str]:
    """{'title': '제목은 2글자 이상 입력해 주세요.', ...} 형태로 바꾼다.

    Pydantic 의 오류 하나는 이런 모양이다.
        {'type': 'string_too_short', 'loc': ('title',), 'msg': '...', 'ctx': {'min_length': 2}}
    여기서 type 과 loc 을 보고 우리 문구로 갈아끼운다.
    """
    result: dict[str, str] = {}
    for error in exc.errors():
        field = str(error["loc"][0]) if error["loc"] else "unknown"
        label = FIELD_NAMES.get(field, field)
        etype = error["type"]
        ctx = error.get("ctx") or {}

        if etype in ("missing", "string_too_short") and field in ("title", "content"):
            minimum = ctx.get("min_length", 1)
            if minimum > 1:
                message = f"{label}은(는) {minimum}글자 이상 입력해 주세요."
            else:
                message = f"{label}을(를) 입력해 주세요."
        elif etype == "string_too_long":
            message = f"{label}은(는) {ctx.get('max_length')}글자를 넘을 수 없습니다."
        elif etype in ("int_parsing", "int_type"):
            message = f"{label}은(는) 숫자로 입력해 주세요. (예: 90)"
        elif etype == "greater_than_equal":
            message = f"{label}은(는) {ctx.get('ge')}분 이상이어야 합니다."
        elif etype == "less_than_equal":
            message = f"{label}은(는) {ctx.get('le')}분을 넘을 수 없습니다. (하루는 1440분)"
        elif etype in ("date_from_datetime_parsing", "date_parsing", "date_type"):
            message = f"{label}은(는) YYYY-MM-DD 형식으로 입력해 주세요."
        elif etype == "value_error":
            # field_validator 안에서 raise ValueError(...) 한 경우. 우리가 쓴 문구를 그대로 쓴다.
            message = str(ctx.get("error", "")) or f"{label}이(가) 올바르지 않습니다."
        else:
            message = f"{label}이(가) 올바르지 않습니다."

        # 한 필드에 오류가 여러 개면 첫 번째만 보여준다. 화면이 복잡해지지 않도록.
        result.setdefault(field, message)
    return result
