"""models/study_log.py — SQLAlchemy ORM 모델 (DB 테이블의 파이썬 표현).

■ ORM 이 하는 일
  파이썬 클래스 ↔ DB 테이블을 짝지어 준다.
  `StudyLog(title="...")` 를 만들고 session.add() 하면
  SQLAlchemy 가 `INSERT INTO study_logs (...) VALUES (...)` 를 대신 만들어 실행한다.
  즉 SQL 문자열을 손으로 쓰지 않아도 되고, 오타가 나면 실행 전에 파이썬이 잡아준다.

■ 필드를 이렇게 고른 이유 (과제 권장: 3~6개)
  학습 기록을 남기려면 "무엇을(title) 얼마나(minutes) 언제(studied_on) 어떤 분야에서(category)
  어떻게(content)" 가 필요하다. 5개로 고정했다.

■ category 를 문자열로 둔 이유 ★ 평가에서 물어볼 수 있음
  지금은 단일 모델만 쓰는 과제라 관계(relationship)를 만들지 않았다.
  나중에 카테고리를 별도 테이블로 분리한다면
  ① Category 모델을 만들고 ② 여기 category 를 category_id = ForeignKey 로 바꾸고
  ③ relationship 을 걸고 ④ 저장소의 조회에 join 을 추가하면 된다.
  라우터와 템플릿은 서비스가 돌려주는 DTO 모양만 유지하면 거의 그대로 쓸 수 있다.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class StudyLog(Base):
    """학습 기록 한 건 = study_logs 테이블의 한 행."""

    __tablename__ = "study_logs"

    # Mapped[...] + mapped_column(...) 은 SQLAlchemy 2.0 스타일이다.
    # 타입 힌트(Mapped[int])가 곧 컬럼 타입 정보가 되어, 편집기가 log.title 을 문자열로 안다.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # index=True : 제목 검색(보너스 기능)이 많으므로 인덱스를 만들어 둔다
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Text 는 길이 제한이 없는 문자열. 본문은 길어질 수 있다.
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 언제 공부했는지 (사용자가 입력)
    studied_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 몇 분 공부했는지
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 분야 (예: Python, Web, Linux)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="etc", index=True)

    # 레코드가 만들어진 시각 (사용자 입력이 아니라 DB 가 채운다)
    # server_default=func.now() 는 "DB 야 네가 지금 시각을 넣어라"는 뜻이다.
    # 파이썬에서 datetime.now() 를 넣는 것과 달리, 서버 시간대가 아니라 DB 기준이 된다.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        """디버깅할 때 객체가 뭔지 바로 보이도록."""
        return f"<StudyLog id={self.id} title={self.title!r} minutes={self.minutes}>"
