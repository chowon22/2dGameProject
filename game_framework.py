"""모드(화면) 전환과 메인 루프.

각 모드 모듈은 init / finish / handle_events / update / draw 를 가진다.
pause / resume 은 push_mode / pop_mode 를 쓸 때만 필요하다.
"""
import time

running = False
stack = []
frame_time = 0.0  # 직전 프레임에 걸린 시간(초). 모든 움직임은 이 값을 곱해 속도를 맞춘다.


def change_mode(mode):
    if stack:
        stack[-1].finish()
        stack.pop()
    stack.append(mode)
    mode.init()


def push_mode(mode):
    if stack:
        stack[-1].pause()
    stack.append(mode)
    mode.init()


def pop_mode():
    if stack:
        stack[-1].finish()
        stack.pop()
    if stack:
        stack[-1].resume()


def quit():
    global running
    running = False


def run(start_mode):
    global running, frame_time
    running = True
    stack.clear()
    stack.append(start_mode)
    start_mode.init()

    current = time.time()
    while running:
        mode = stack[-1]
        mode.handle_events()
        if not running:
            break
        mode.update()
        mode.draw()
        now = time.time()
        frame_time = min(now - current, 0.1)  # 창을 끌 때 같은 긴 멈춤 뒤 순간이동 방지
        current = now

    while stack:
        stack[-1].finish()
        stack.pop()
