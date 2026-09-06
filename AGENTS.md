# pet

PyQt6로 만든 macOS 데스크톱 펫. `pet.py` 한 파일이 전부다.

## 실행
source .venv/bin/activate && python3 pet.py sprite.png

## 반드시 지킬 것
- 도트가 뿌옇게 되면 안 된다. `paintEvent`에서 정수 배율로만 확대하고
  `SmoothPixmapTransform`과 `Antialiasing`은 꺼진 상태를 유지한다.
- 창은 투명·테두리 없음·항상 위. 이 세 플래그를 건드리지 않는다.
- 위치는 `self.fx`, `self.fy`에 소수로 들고 있다가 그릴 때만 정수로 옮긴다.
  정수로 직접 계산하면 움직임이 끊긴다.
- 파일을 새로 만들지 말고 `pet.py`만 수정한다.
