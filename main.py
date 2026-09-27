"""main.py — FastAPI 애플리케이션 진입점.

실행:  uvicorn main:app --reload
      (main 파일의 app 객체를 찾아서 띄워라 는 뜻)

■ 이 파일이 하는 일은 '조립'뿐이다
  - 앱을 만들고
  - 시작할 때 테이블을 만들고
  - 라우터를 등록하고
  - 정적 파일 경로를 연결한다
  업무 로직은 한 줄도 없다. 어떤 부품이 있는지 한눈에 보이는 것이 이 파일의 역할이다.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers import home, study_logs
from templating import templates

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버가 뜨고 질 때 할 일.

    yield 앞 = 시작할 때 (테이블 생성)
    yield 뒤 = 종료할 때 (지금은 할 일 없음)

    예전에는 @app.on_event("startup") 을 썼지만 지금은 이 방식이 권장된다.
    """
    init_db()
    print("[startup] 데이터베이스 준비 완료 → http://localhost:8000")
    yield


app = FastAPI(
    title="학습 로그",
    description="공부한 내용을 기록하고 목록/상세/수정/삭제할 수 있는 작은 웹 서비스",
    lifespan=lifespan,
)

# 정적 파일(CSS). /static/style.css 로 접근된다.
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 라우터 등록. 이 줄이 없으면 아무 주소도 열리지 않는다.
app.include_router(home.router)
app.include_router(study_logs.router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc) -> HTMLResponse:
    """주소 자체가 없을 때(예: /없는주소) 보여줄 화면.

    라우터 안의 _not_found_page 는 '주소는 맞지만 데이터가 없을 때'를 담당하고,
    이 핸들러는 '주소가 아예 없을 때'를 담당한다.
    """
    return templates.TemplateResponse(
        request=request,
        name="not_found.html",
        context={"log_id": None, "path": request.url.path},
        status_code=404,
    )
