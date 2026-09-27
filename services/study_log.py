"""services/study_log.py — 서비스 계층. 업무 규칙을 담당한다.

■ 이 계층이 답하는 질문
  - 이 입력이 규칙에 맞는가? (검증)
  - 없는 글을 수정하려 하면 어떻게 되는가? (예외)
  - 화면에 넘길 데이터는 어떤 모양이어야 하는가? (ORM → DTO 변환)

■ 이 계층이 하지 않는 일
  - HTTP 를 모른다. Request, Response, 상태코드, 리다이렉트가 이 파일에 하나도 없다.
    그래서 나중에 REST API 로 바꾸거나 CLI 를 붙여도 이 파일은 그대로 쓸 수 있다.
  - SQL 을 직접 쓰지 않는다. 저장소에게 부탁한다.

■ NotFoundError 를 여기서 정의한 이유
  "없는 글"은 업무적으로 의미 있는 상황이지 HTTP 개념이 아니다.
  서비스는 업무 언어로 신호를 보내고, 그걸 404 화면으로 바꿀지는 라우터가 정한다.
"""

from sqlalchemy.orm import Session

from models.study_log import StudyLog
from repositories.study_log import StudyLogRepository
from schemas.study_log import StudyLogCreate, StudyLogRead, StudyLogUpdate


class StudyLogNotFound(Exception):
    """요청한 학습 기록이 없을 때."""

    def __init__(self, log_id: int) -> None:
        super().__init__(f"id={log_id} 인 학습 기록을 찾을 수 없습니다.")
        self.log_id = log_id


class StudyLogService:
    """학습 기록의 업무 규칙."""

    def __init__(self, db: Session) -> None:
        # 서비스가 저장소를 만든다. 라우터는 저장소의 존재를 몰라도 된다.
        self.repo = StudyLogRepository(db)

    # ---------- 조회 ----------

    def list(self, keyword: str | None = None) -> list[StudyLogRead]:
        """목록을 DTO 로 바꿔 돌려준다.

        여기서 ORM 객체를 그대로 넘기지 않는 것이 핵심이다.
        템플릿은 StudyLogRead 만 알면 되고, DB 세션이 닫혀도 안전하다.
        """
        keyword = (keyword or "").strip()
        rows = self.repo.list(keyword or None)
        return [StudyLogRead.model_validate(row) for row in rows]

    def get(self, log_id: int) -> StudyLogRead:
        """한 건. 없으면 StudyLogNotFound 를 던진다."""
        row = self.repo.get(log_id)
        if row is None:
            raise StudyLogNotFound(log_id)
        return StudyLogRead.model_validate(row)

    def stats(self) -> dict[str, int]:
        """홈 화면에 보여줄 간단한 통계."""
        return {
            "count": self.repo.count(),
            "total_minutes": self.repo.total_minutes(),
        }

    # ---------- 변경 ----------

    def create(self, data: StudyLogCreate) -> StudyLogRead:
        """새 기록을 만든다.

        data 는 이미 Pydantic 이 검증을 통과시킨 값이다.
        즉 이 지점에 도달했다는 것은 "형식은 올바르다"가 보장된 상태다.
        """
        row = StudyLog(
            title=data.title,
            content=data.content,
            studied_on=data.studied_on,
            minutes=data.minutes,
            category=data.category,
        )
        saved = self.repo.create(row)
        return StudyLogRead.model_validate(saved)

    def update(self, log_id: int, data: StudyLogUpdate) -> StudyLogRead:
        """기존 기록을 수정한다. 없으면 예외."""
        row = self.repo.get(log_id)
        if row is None:
            raise StudyLogNotFound(log_id)

        # 세션이 추적 중인 객체의 속성을 바꾸면, commit 때 UPDATE 가 나간다.
        row.title = data.title
        row.content = data.content
        row.studied_on = data.studied_on
        row.minutes = data.minutes
        row.category = data.category

        saved = self.repo.update(row)
        return StudyLogRead.model_validate(saved)

    def delete(self, log_id: int) -> StudyLogRead:
        """삭제하고, 삭제된 내용을 돌려준다(화면에 '무엇을 지웠는지' 보여주기 위해).

        DTO 변환을 삭제 '전에' 하는 이유:
          삭제 후에는 그 객체가 세션에서 떨어져 나가 속성 접근이 안전하지 않다.
        """
        row = self.repo.get(log_id)
        if row is None:
            raise StudyLogNotFound(log_id)
        snapshot = StudyLogRead.model_validate(row)
        self.repo.delete(row)
        return snapshot
