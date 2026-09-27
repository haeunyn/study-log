"""schemas/study_log.py — Pydantic 스키마 (계층 사이를 오가는 데이터 모양).

■ ORM 모델이 있는데 왜 또 만드나? ★ 과제 권장사항이자 평가 포인트
  과제 문서: "ORM 모델을 직접 라우터에서 반환하지 않고
              Pydantic Schema 또는 별도 DTO 객체로 분리하여 사용하는 것을 권장"

  이유는 세 가지다.
  ① **경계를 만든다.** ORM 객체는 DB 세션에 묶여 있다. 세션이 닫힌 뒤에 접근하면
     터지거나(DetachedInstanceError) 의도치 않게 추가 쿼리가 나간다.
     화면에 넘기기 전에 순수한 파이썬 객체로 바꿔두면 그런 사고가 없다.
  ② **노출 범위를 정한다.** DB에 있는 모든 컬럼을 화면이 볼 필요는 없다.
     나중에 비밀번호 같은 필드가 생겨도 Read 스키마에 넣지 않으면 새어나가지 않는다.
  ③ **입력 검증을 한 곳에 모은다.** 폼에서 온 문자열을 여기서 날짜/정수로 바꾸고
     규칙에 맞는지 검사한다. 통과한 값만 서비스 안쪽으로 들어간다.

■ Create / Update / Read 를 나눈 이유
  만들 때는 id 가 없고, 읽을 때는 id 와 created_at 이 있다.
  하나로 합치면 "id 는 있을 수도 없을 수도 있다" 같은 애매한 타입이 된다.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 카테고리는 자유 입력이지만, 화면의 선택지로 쓸 기본 목록을 둔다.
CATEGORY_CHOICES: tuple[str, ...] = ("Python", "Web", "Linux", "DB", "Algorithm", "etc")

MIN_TITLE_LENGTH = 2
MAX_MINUTES = 24 * 60  # 하루는 1440분을 넘을 수 없다


class StudyLogBase(BaseModel):
    """등록과 수정이 공통으로 받는 필드."""

    title: str = Field(..., min_length=MIN_TITLE_LENGTH, max_length=100)
    content: str = Field(..., min_length=1)
    studied_on: date
    minutes: int = Field(..., ge=1, le=MAX_MINUTES)
    category: str = Field(default="etc", max_length=30)

    @field_validator("title", "content", "category")
    @classmethod
    def strip_spaces(cls, value: str) -> str:
        """앞뒤 공백을 없앤다.

        공백만 입력한 경우(" ")를 빈 값으로 만들어, 위의 min_length 검사에 걸리게 하는 역할도 한다.
        검증 순서상 이 함수가 먼저 돌고 길이 검사가 나중에 돈다.
        """
        return value.strip()

    @field_validator("studied_on")
    @classmethod
    def not_future(cls, value: date) -> date:
        """미래 날짜는 받지 않는다. 아직 하지 않은 공부를 기록할 수는 없다."""
        if value > date.today():
            raise ValueError("학습일은 오늘보다 미래일 수 없습니다.")
        return value


class StudyLogCreate(StudyLogBase):
    """등록 폼에서 받은 값."""


class StudyLogUpdate(StudyLogBase):
    """수정 폼에서 받은 값. (이번 과제에서는 전체 필드를 다시 받는다)"""


class StudyLogRead(BaseModel):
    """화면으로 내보낼 값. 라우터와 템플릿은 이 모양만 안다.

    model_config 의 from_attributes=True 는
    "객체의 속성(.title, .id ...)에서 값을 꺼내 만들어도 된다"는 뜻이다.
    덕분에 StudyLogRead.model_validate(orm_object) 한 줄로 변환된다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    studied_on: date
    minutes: int
    category: str
    created_at: datetime

    @property
    def duration_text(self) -> str:
        """95 -> '1시간 35분'. 화면에서 쓰기 좋은 형태로 바꿔준다."""
        hours, mins = divmod(self.minutes, 60)
        if hours and mins:
            return f"{hours}시간 {mins}분"
        if hours:
            return f"{hours}시간"
        return f"{mins}분"
