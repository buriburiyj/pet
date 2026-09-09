- 09/09 00:08

cd ~/dev/pet && git add -A && git commit -qm "feat: 타이머 분 입력, 클립 기록 골라 지우기" && git push -q && echo "완료"

- 09/09 00:11

cd ~/dev/pet && python3 - <<'PY'
import pathlib, py_compile
p = pathlib.Path('pet.py')
s = p.read_text()
anchor = "sys.exit(app.exec())"
if "종료 요청 응답" in s:
    print("이미 들어가 있음"); raise SystemExit
block = '''
# ==== 종료 요청 응답 ====
try:
    import signal as _sg
    app.setQuitOnLastWindowClosed(True)

    def _bye(*a):
        try:
            pet.close()
        except Exception:
            pass
        app.quit()

    for _n in (_sg.SIGTERM, _sg.SIGINT, _sg.SIGHUP):
        _sg.signal(_n, _bye)

    _sgt = QTimer(pet)
    _sgt.timeout.connect(lambda: None)
    _sgt.start(200)

    try:
        from AppKit import NSApplication as _NSA2
        _NSA2.sharedApplication().delegate()
    except Exception:
        pass
    print("종료 요청 응답 등록됨")
except Exception as _e:
    print("종료 응답 실패:", _e)

'''
s = s.replace(anchor, block + anchor, 1)
p.write_text(s)
py_compile.compile('pet.py', doraise=True)
print("추가됨, 문법 정상")
PY
pkill -f pet.py; sleep 1; source .venv/bin/activate && python3 pet.py sprite.png

- 09/09 14:22

cd ~/dev/pet && git add -A && git commit -qm "fix: 로그아웃 시 스스로 종료" && git push -q && echo "완료"

