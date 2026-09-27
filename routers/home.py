"""routers/home.py — 홈 화면 라우터.

라우터의 책임은 세 가지뿐이다.
  ① 요청에서 값을 꺼낸다
  ② 서비스에게 시킨다
  ③ 결과를 화면(또는 리다이렉트)으로 바꾼다
계산도, DB 접근도 여기서 하지 않는다.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from services.study_log import StudyLogService
from templating import templates

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """GET / — 앱 설명과 이동 링크가 있는 홈 화면.

    Depends(get_db) 가 하는 일:
      요청이 들어오면 FastAPI 가 get_db() 를 실행해 세션을 만들고 이 함수에 넣어준다.
      응답이 나간 뒤에는 get_db() 의 finally 가 실행되어 세션이 닫힌다.
      즉 세션의 수명은 요청 하나와 정확히 같다.
    """
    service = StudyLogService(db)
    stats = service.stats()
    recent = service.list()[:3]  # 최근 3건만 미리보기

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"stats": stats, "recent": recent},
    )
