"""routers/study_logs.py — 학습 기록 CRUD 라우터. ★ 이 과제의 핵심

■ 화면 흐름 (과제 요구: 홈/목록/상세/등록/수정 최소 5개)
    GET  /logs               목록 (?q= 로 검색 — 보너스 1)
    GET  /logs/new           등록 폼
    POST /logs               등록 처리 → 303 리다이렉트
    GET  /logs/{id}          상세
    GET  /logs/{id}/edit     수정 폼
    POST /logs/{id}/edit     수정 처리 → 303 리다이렉트
    POST /logs/{id}/delete   삭제 처리 → 303 리다이렉트

■ GET 과 POST 를 나누는 이유 ★ 평가 문항
  GET  = "조회". 같은 요청을 몇 번 보내도 서버 상태가 변하지 않는다(멱등).
         그래서 브라우저가 주소창에 남기고, 북마크·뒤로가기·새로고침이 자유롭다.
  POST = "변경". 서버 상태를 바꾼다. 몇 번 보내면 그만큼 일이 일어난다.
  만약 삭제를 GET 으로 만들면, 브라우저나 검색엔진이 링크를 미리 훑는 것만으로
  데이터가 지워질 수 있다. 그래서 변경은 반드시 POST 로 받는다.

■ PRG(Post-Redirect-Get) 패턴 ★ 평가 문항
  POST 를 처리한 뒤 **화면을 직접 그리지 않고** 리다이렉트를 돌려준다.
  안 그러면 사용자가 F5 를 누를 때 브라우저가 "POST 를 다시 보낼까요?" 를 묻고,
  확인을 누르면 **같은 글이 또 등록된다.**
  리다이렉트를 돌려주면 주소창이 GET 주소로 바뀌므로, 새로고침해도 GET 이 다시 갈 뿐이다.

■ 왜 303 인가?
  302 는 "다시 보낼 때 원래 메서드를 유지해도 된다"는 해석의 여지가 있어,
  일부 클라이언트가 POST 로 다시 요청한다.
  303 See Other 는 규격상 **반드시 GET 으로 바꿔서** 요청하라는 뜻이다.
  그래서 POST 뒤의 리다이렉트에는 303 이 정확한 선택이다.
  (307/308 은 반대로 메서드를 '유지'하라는 뜻이라 여기서는 쓰면 안 된다)
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import get_db
from form_errors import to_korean_errors
from schemas.study_log import CATEGORY_CHOICES, StudyLogCreate, StudyLogUpdate
from services.study_log import StudyLogNotFound, StudyLogService
from templating import templates

router = APIRouter(prefix="/logs", tags=["study-logs"])


def _not_found_page(request: Request, log_id: int):
    """없는 글을 찾았을 때 보여줄 안내 화면.

    과제 요구: "존재하지 않는 데이터 조회 시 적절한 안내 화면이 표시되거나 목록으로 이동"
    상태 코드를 404 로 주는 것이 중요하다. 화면만 안내문이고 200 을 주면
    검색엔진이나 모니터링 도구는 '정상'으로 오해한다.
    """
    return templates.TemplateResponse(
        request=request,
        name="not_found.html",
        context={"log_id": log_id},
        status_code=404,
    )


# ============================================================
# 목록
# ============================================================


@router.get("", response_class=HTMLResponse)
def list_logs(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    """GET /logs — 목록. ?q=키워드 로 제목 검색. (보너스 1)

    검색어를 쿼리 파라미터(?q=)로 받는 이유:
      검색은 '조회'이므로 GET 이고, 주소에 조건이 남아야 링크를 공유하거나
      뒤로가기를 눌렀을 때 같은 결과가 다시 보인다.
    """
    service = StudyLogService(db)
    logs = service.list(q)
    return templates.TemplateResponse(
        request=request,
        name="list.html",
        context={"logs": logs, "keyword": q or ""},
    )


# ============================================================
# 등록
# ============================================================
# ⚠️ 순서 주의: "/logs/new" 는 "/logs/{log_id}" 보다 **먼저** 선언해야 한다.
#    FastAPI 는 선언된 순서대로 경로를 맞춰보는데, {log_id} 가 먼저 있으면
#    "new" 를 정수 id 로 해석하려다 422 오류가 난다.


@router.get("/new", response_class=HTMLResponse)
def new_form(request: Request):
    """GET /logs/new — 빈 등록 폼."""
    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "mode": "create",
            "action": "/logs",
            "values": {"category": "etc", "minutes": 60},
            "errors": {},
            "categories": CATEGORY_CHOICES,
        },
    )


@router.post("")
def create_log(
    request: Request,
    title: str = Form(default=""),
    content: str = Form(default=""),
    studied_on: str = Form(default=""),
    minutes: str = Form(default=""),
    category: str = Form(default="etc"),
    db: Session = Depends(get_db),
):
    """POST /logs — 등록 처리. 성공하면 상세 화면으로 303 리다이렉트.

    ■ 폼 값이 어떻게 여기까지 오는가 ★ 평가 문항
      ① 브라우저가 <form method="post"> 를 제출하면 입력값을
         `title=...&content=...` 형태(application/x-www-form-urlencoded)로 본문에 담아 보낸다.
      ② FastAPI 가 그 본문을 파싱한다. 이때 python-multipart 패키지가 필요하다.
      ③ Form(default="") 로 선언한 매개변수에 값이 꽂힌다. **이 시점에는 전부 문자열**이다.
      ④ 그 문자열을 Pydantic 모델(StudyLogCreate)에 넣으면
         "2026-09-27" → date, "90" → int 로 바꾸면서 규칙까지 검사한다.

    ■ 왜 Form 매개변수를 전부 str 로 받나?
      `minutes: int = Form(...)` 로 선언하면 숫자가 아닐 때 FastAPI 가 422 JSON 오류를 낸다.
      사용자에게 보여줄 화면이 아니라 개발자용 응답이다.
      전부 문자열로 받아서 Pydantic 으로 직접 검증하면, 실패했을 때
      **입력값을 그대로 유지한 폼을 다시 그려줄 수 있다.** (보너스 2)
    """
    raw = {
        "title": title,
        "content": content,
        "studied_on": studied_on,
        "minutes": minutes,
        "category": category,
    }
    try:
        data = StudyLogCreate(**raw)
    except ValidationError as exc:
        # 검증 실패: 리다이렉트하지 않고 폼을 다시 그린다.
        # 리다이렉트하면 사용자가 입력한 값이 사라지기 때문이다.
        return templates.TemplateResponse(
            request=request,
            name="form.html",
            context={
                "mode": "create",
                "action": "/logs",
                "values": raw,
                "errors": to_korean_errors(exc),
                "categories": CATEGORY_CHOICES,
            },
            status_code=400,
        )

    log = StudyLogService(db).create(data)
    # ★ PRG: 화면을 그리지 않고 상세 화면으로 보낸다
    return RedirectResponse(url=f"/logs/{log.id}", status_code=303)


# ============================================================
# 상세 / 수정 / 삭제
# ============================================================


@router.get("/{log_id}", response_class=HTMLResponse)
def detail(request: Request, log_id: int, db: Session = Depends(get_db)):
    """GET /logs/{id} — 상세. 전체 필드와 수정/삭제/목록 링크를 보여준다."""
    try:
        log = StudyLogService(db).get(log_id)
    except StudyLogNotFound:
        return _not_found_page(request, log_id)
    return templates.TemplateResponse(request=request, name="detail.html", context={"log": log})


@router.get("/{log_id}/edit", response_class=HTMLResponse)
def edit_form(request: Request, log_id: int, db: Session = Depends(get_db)):
    """GET /logs/{id}/edit — 기존 값이 채워진 수정 폼."""
    try:
        log = StudyLogService(db).get(log_id)
    except StudyLogNotFound:
        return _not_found_page(request, log_id)

    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "mode": "edit",
            "action": f"/logs/{log_id}/edit",
            "values": {
                "title": log.title,
                "content": log.content,
                "studied_on": log.studied_on.isoformat(),
                "minutes": log.minutes,
                "category": log.category,
            },
            "errors": {},
            "categories": CATEGORY_CHOICES,
            "log_id": log_id,
        },
    )


@router.post("/{log_id}/edit")
def update_log(
    request: Request,
    log_id: int,
    title: str = Form(default=""),
    content: str = Form(default=""),
    studied_on: str = Form(default=""),
    minutes: str = Form(default=""),
    category: str = Form(default="etc"),
    db: Session = Depends(get_db),
):
    """POST /logs/{id}/edit — 수정 처리 → 상세 화면으로 303."""
    raw = {
        "title": title,
        "content": content,
        "studied_on": studied_on,
        "minutes": minutes,
        "category": category,
    }
    try:
        data = StudyLogUpdate(**raw)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="form.html",
            context={
                "mode": "edit",
                "action": f"/logs/{log_id}/edit",
                "values": raw,
                "errors": to_korean_errors(exc),
                "categories": CATEGORY_CHOICES,
                "log_id": log_id,
            },
            status_code=400,
        )

    try:
        StudyLogService(db).update(log_id, data)
    except StudyLogNotFound:
        return _not_found_page(request, log_id)

    return RedirectResponse(url=f"/logs/{log_id}", status_code=303)


@router.post("/{log_id}/delete")
def delete_log(request: Request, log_id: int, db: Session = Depends(get_db)):
    """POST /logs/{id}/delete — 삭제 처리 → 목록으로 303.

    삭제를 링크(GET)가 아니라 폼(POST)으로 만든 이유는 이 파일 맨 위 주석 참고.
    """
    try:
        StudyLogService(db).delete(log_id)
    except StudyLogNotFound:
        return _not_found_page(request, log_id)
    return RedirectResponse(url="/logs", status_code=303)
