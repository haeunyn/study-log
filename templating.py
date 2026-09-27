"""templating.py — Jinja2 템플릿 엔진 설정.

별도 파일로 뺀 이유:
  main.py 에 두면 routers 가 main 을 import 하고 main 이 routers 를 import 하는
  순환 참조가 생긴다. 양쪽이 모두 참조하는 것은 제3의 파일에 두는 것이 정석이다.
"""

from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

# 과제 요구: "템플릿 파일은 templates/ 디렉터리 아래에 존재해야 한다"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
