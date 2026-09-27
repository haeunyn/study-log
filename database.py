"""database.py — DB 연결과 세션 관리.

■ 이 파일이 하는 일
  1) SQLite 파일에 연결하는 엔진(engine)을 만든다
  2) 세션을 찍어내는 공장(SessionLocal)을 만든다
  3) ORM 모델이 상속할 Base 를 만든다
  4) 요청마다 세션을 열고 닫아주는 get_db() 를 제공한다

■ 세션(Session)이 뭔가?
  DB와의 '대화 한 묶음'이다. 이 안에서 조회하고 수정한 내용은
  commit() 하기 전까지 실제 DB에 반영되지 않는다.
  요청 하나에 세션 하나를 쓰는 이유는, 요청 처리 중 실패하면
  그 요청에서 한 작업 전체를 없던 일로 되돌릴 수 있게 하기 위해서다.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# DB 파일 위치. 프로젝트 폴더 안에 database.db 로 만들어진다.
# (과제 요구: "DB 파일이 프로젝트 디렉터리에 생성되어야 하며 DB 브라우저로 확인 가능해야 한다")
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'database.db'}"

# check_same_thread=False 를 주는 이유:
#   SQLite 는 기본적으로 "연결을 만든 스레드에서만 써라"고 막는다.
#   FastAPI 는 여러 스레드에서 요청을 처리하므로 이 제한을 풀어야 한다.
#   대신 세션을 요청마다 따로 만들기 때문에(아래 get_db) 충돌하지 않는다.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # True 로 바꾸면 실행되는 SQL 이 터미널에 전부 찍힌다 (학습용으로 유용)
)

# 세션 공장. 필요할 때마다 SessionLocal() 로 새 세션을 찍어낸다.
#   autocommit=False : commit() 을 명시적으로 불러야 저장된다 (실수 방지)
#   autoflush=False  : 조회 직전에 자동으로 flush 하지 않는다 (동작을 예측 가능하게)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """모든 ORM 모델이 상속하는 부모.

    SQLAlchemy 2.0 스타일이다. 이 클래스를 상속한 클래스들의 정보가
    Base.metadata 에 모이고, create_all() 이 그걸 보고 테이블을 만든다.
    """


def get_db() -> Generator[Session, None, None]:
    """요청 하나당 세션 하나를 열고, 끝나면 반드시 닫는다.

    ■ 왜 yield 를 쓰나? (FastAPI 의 의존성 주입 방식)
      yield 앞부분  → 요청 처리 '전'에 실행 (세션 열기)
      yield 로 넘김 → 라우터가 이 세션을 받아서 쓴다
      yield 뒷부분  → 응답이 나간 '후'에 실행 (세션 닫기)
      finally 에 두었으므로 중간에 예외가 나도 세션은 반드시 닫힌다.

    ■ 왜 Depends 로 주입하나?
      각 라우터가 직접 SessionLocal() 을 만들면, 닫는 것을 깜빡하는 순간
      연결이 새어나간다(connection leak). 열고 닫는 책임을 한 곳에 모은 것이다.
      테스트할 때 이 함수만 바꿔치기하면 테스트용 DB로 갈아끼울 수도 있다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """테이블이 없으면 만든다. 서버가 시작할 때 한 번 호출된다.

    이미 있는 테이블은 건드리지 않는다. 운영 환경이라면 이렇게 하지 않고
    Alembic 같은 마이그레이션 도구를 쓰지만, 이번 과제 범위에서는 이걸로 충분하다.
    """
    # 모델을 import 해야 Base.metadata 에 등록된다. (등록되지 않으면 테이블이 안 생긴다)
    from models import study_log  # noqa: F401

    Base.metadata.create_all(bind=engine)
