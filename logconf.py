# 로깅 설정을 한 곳에 모아둔 모듈.
#
# 왜 print가 아니라 logging인가:
#   클라우드에서 돌면 사람이 콘솔을 안 본다. 나중에 Actions 로그를 훑을 때
#   "그냥 진행 상황(INFO)"인지 "뭔가 잘못됨(WARNING/ERROR)"인지 구분돼야
#   눈으로 걸러낼 수 있다. print는 전부 똑같이 보인다.
#
# 왜 import 시점이 아니라 setup() 호출인가:
#   import만으로 전역 상태(stdout 인코딩, 루트 로거)를 바꾸면
#   테스트에서 예측 불가능해진다. 부수효과는 진입점에서만 일으킨다.

import logging
import sys


def setup(level: int = logging.INFO) -> None:
    """진입점(main)에서 한 번만 호출한다. 한글 출력 + 심각도 표시."""
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=level,
        format="%(levelname)s | %(message)s",
        stream=sys.stdout,
    )
