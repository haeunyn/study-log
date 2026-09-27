"""repositories/study_log.py — 저장소 계층. DB 접근'만' 한다.

■ 이 계층의 약속
  - 여기서는 "무엇이 올바른 입력인가"를 판단하지 않는다. 그건 서비스의 일이다.
  - 여기는 SELECT / INSERT / UPDATE / DELETE 에 해당하는 동작만 한다.
  - commit 도 여기서 한다. 한 동작이 곧 하나의 저장 단위이기 때문이다.

■ 왜 라우터에서 바로 db.query(...) 를 쓰지 않나? ★ 평가 단골 질문
  ① 같은 조회가 여러 화면에서 필요해진다. 라우터마다 복사하면 조건이 어긋난다.
  ② DB를 바꾸거나 쿼리를 튜닝할 때 고칠 곳이 흩어진다.
  ③ 테스트할 때 저장소만 가짜로 바꿔치기하면 서비스 로직만 따로 검증할 수 있다.

■ SQLAlchemy 메서드가 실제로 무슨 SQL 인가? (항목2에서 물어봄)
  session.add(obj)      → INSERT 할 대상을 세션에 '등록'만 한다. 아직 DB로 가지 않는다.
  session.commit()      → 지금까지 등록된 변경을 모아 실제로 INSERT/UPDATE/DELETE 를 보내고 커밋한다.
  session.refresh(obj)  → 방금 저장된 행을 다시 읽어 id, created_at 처럼 DB가 채운 값을 가져온다.
  session.get(M, pk)    → SELECT ... WHERE id = ? (기본키 조회 전용, 캐시가 있으면 쿼리를 생략)
  select(M)             → SELECT 문을 만드는 2.0 스타일 문법. 실행은 session.scalars(...) 가 한다.
  session.delete(obj)   → DELETE 할 대상을 등록. 역시 commit 때 실제로 나간다.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.study_log import StudyLog


class StudyLogRepository:
    """study_logs 테이블에 대한 접근을 모아둔 클래스.

    세션을 생성자에서 받는 이유:
      요청마다 세션이 다르므로, 저장소도 요청마다 그 세션을 쥐고 만들어진다.
      (라우터가 Depends(get_db) 로 받은 세션을 그대로 넘겨준다)
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- 조회 ----------

    def list(self, keyword: str | None = None) -> list[StudyLog]:
        """전체 목록을 최신순으로. keyword 가 있으면 제목으로 검색한다. (보너스 1)

        정렬 기준이 (studied_on desc, id desc) 인 이유:
          같은 날 기록이 여러 건이면 순서가 흔들린다. id 는 나중에 넣을수록 크므로
          같은 날짜 안에서는 최근에 등록한 것이 위로 온다.

        ilike 를 쓰는 이유:
          like 는 대소문자를 구분한다. 'python' 으로 검색해도 'Python' 이 나오게 하려면 ilike 다.
          `%키워드%` 는 "앞뒤에 무엇이 오든 이 글자가 들어 있으면" 이라는 뜻이다.
        """
        stmt = select(StudyLog)
        if keyword:
            stmt = stmt.where(StudyLog.title.ilike(f"%{keyword}%"))
        stmt = stmt.order_by(StudyLog.studied_on.desc(), StudyLog.id.desc())
        return list(self.db.scalars(stmt).all())

    def get(self, log_id: int) -> StudyLog | None:
        """기본키로 한 건. 없으면 None 을 돌려준다.

        여기서 예외를 던지지 않는 이유:
          "없다"는 것은 저장소 입장에서 오류가 아니라 사실이다.
          그것을 오류로 취급할지(404 화면) 아닌지는 서비스/라우터가 정한다.
        """
        return self.db.get(StudyLog, log_id)

    def count(self) -> int:
        """전체 건수. 홈 화면에서 보여준다."""
        return len(list(self.db.scalars(select(StudyLog.id)).all()))

    def total_minutes(self) -> int:
        """총 학습 시간(분). 홈 화면 통계용."""
        return sum(self.db.scalars(select(StudyLog.minutes)).all())

    # ---------- 변경 ----------

    def create(self, log: StudyLog) -> StudyLog:
        """새 행을 저장하고, DB가 채운 값(id, created_at)까지 반영해서 돌려준다."""
        self.db.add(log)       # ① 세션에 등록 (아직 DB에 안 감)
        self.db.commit()       # ② 실제로 INSERT 가 나가고 커밋된다
        self.db.refresh(log)   # ③ DB가 만든 id/created_at 을 객체에 채운다
        return log

    def update(self, log: StudyLog) -> StudyLog:
        """이미 세션이 추적 중인 객체의 변경을 저장한다.

        add() 를 다시 부르지 않는 이유:
          session.get() 으로 가져온 객체는 이미 세션이 '추적'하고 있다.
          속성을 바꾸면 세션이 변경을 감지(dirty checking)하고, commit 때 UPDATE 를 보낸다.
        """
        self.db.commit()
        self.db.refresh(log)
        return log

    def delete(self, log: StudyLog) -> None:
        self.db.delete(log)
        self.db.commit()
