"""이름 칸: 눌러서 한글·영어로 이름을 적는 한 줄 입력 칸 (유닛 추가하기·내 유닛).

pico2d 의 get_events 는 글자 입력(SDL_TEXTINPUT)·조합 중인 한글(SDL_TEXTEDITING) 이벤트를 버려서,
이 모듈의 get_events 를 대신 쓴다 (pico2d 와 같은 Event 에 text 를 더해 준다).
글자 입력(IME)은 칸을 누른 동안만 켜고 (SDL_StartTextInput), 끝나면 다시 끈다 — 평소엔 글자 키가 단축키로 가게.
- 누르면 적기 시작, Enter·Esc·칸 밖 누르기로 끝 (끝날 때 on_done(이름))
- 적는 동안 Backspace 로 지우기. 조합 중인 한글은 밑줄 대신 옅은 색으로 이어 보인다
open_canvas() 뒤에만 쓸 수 있다.
"""
import ctypes

from pico2d import draw_rectangle
import pico2d.pico2d as _p
from sdl2 import (SDL_Event, SDL_PollEvent, SDL_Delay, SDL_QUIT, SDL_KEYDOWN, SDL_KEYUP, SDL_MOUSEMOTION,
                  SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP, SDL_MOUSEWHEEL, SDL_TEXTINPUT, SDL_TEXTEDITING,
                  SDL_StartTextInput, SDL_StopTextInput, SDLK_BACKSPACE, SDLK_RETURN, SDLK_KP_ENTER, SDLK_ESCAPE)

import save_data
import text

INK = (86, 68, 106)
SOFT = (170, 154, 186)
BOX = (255, 252, 247)
BOX_ON = (255, 246, 214)


def get_events():
    """pico2d.get_events 와 같고, 글자 입력 이벤트(type SDL_TEXTINPUT / SDL_TEXTEDITING, .text)도 준다."""
    _p.print_fps()
    SDL_Delay(1)
    e = SDL_Event()
    out = []
    while SDL_PollEvent(ctypes.byref(e)):
        ev = _p.Event(e.type)
        if e.type == SDL_QUIT:
            out.append(ev)
        elif e.type in (SDL_KEYDOWN, SDL_KEYUP):
            if e.type == SDL_KEYDOWN and e.key.keysym.sym == SDLK_BACKSPACE or not e.key.repeat:
                ev.key = e.key.keysym.sym   # 지우기는 꾹 누르면 이어서
                out.append(ev)
        elif e.type == SDL_MOUSEMOTION:
            ev.x, ev.y = e.motion.x, e.motion.y
            out.append(ev)
        elif e.type in (SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP):
            ev.button, ev.x, ev.y = e.button.button, e.button.x, e.button.y
            out.append(ev)
        elif e.type == SDL_MOUSEWHEEL:
            ev.x, ev.y = e.wheel.x, e.wheel.y
            out.append(ev)
        elif e.type == SDL_TEXTINPUT:
            ev.text = e.text.text.decode('utf-8', 'ignore')
            out.append(ev)
        elif e.type == SDL_TEXTEDITING:
            ev.text = e.edit.text.decode('utf-8', 'ignore')
            out.append(ev)
    return out


class NameField:
    """(x, y) 가 왼쪽 가운데인 폭 w 이름 칸."""
    H = 34

    def __init__(self, x, y, w, on_done=None):
        self.x, self.y, self.w = x, y, w
        self.value = ''
        self.composing = ''     # 조합 중인 한글
        self.active = False
        self.on_done = on_done
        self.t = 0.0

    def contains(self, mx, my):
        return self.x <= mx <= self.x + self.w and abs(my - self.y) <= self.H / 2

    def start(self):
        if not self.active:
            self.active = True
            self.composing = ''
            self.t = 0.0
            SDL_StartTextInput()

    def stop(self):
        if self.active:
            self.active = False
            if self.composing:   # 조합 중이던 글자도 넣는다
                self._add(self.composing)
                self.composing = ''
            SDL_StopTextInput()
            if self.on_done:
                self.on_done(self.value)

    def click(self, mx, my):
        """칸을 눌렀으면 적기 시작하고 True. 적던 중 칸 밖을 누르면 끝내고 False."""
        if self.contains(mx, my):
            self.start()
            return True
        self.stop()
        return False

    def _add(self, s):
        self.value = (self.value + s)[:save_data.NAME_MAX]

    def handle(self, ev):
        """적는 중이면 이 이벤트를 쓰고 True (화면은 단축키 등으로 쓰지 않는다)."""
        if not self.active:
            return False
        if ev.type == SDL_TEXTINPUT:
            self.composing = ''
            self._add(ev.text)
        elif ev.type == SDL_TEXTEDITING:
            self.composing = ev.text
        elif ev.type == SDL_KEYDOWN:
            if ev.key in (SDLK_RETURN, SDLK_KP_ENTER, SDLK_ESCAPE):
                self.stop()
            elif ev.key == SDLK_BACKSPACE and not self.composing:   # 조합 중이면 입력기가 지운다
                self.value = self.value[:-1]
        elif ev.type != SDL_KEYUP:
            return False
        return True

    def update(self, dt):
        self.t += dt

    def draw(self, placeholder=''):
        x1, x2 = self.x, self.x + self.w
        y1, y2 = self.y - self.H / 2, self.y + self.H / 2
        draw_rectangle(x1, y1, x2, y2, *(BOX_ON if self.active else BOX), filled=True)
        draw_rectangle(x1, y1, x2, y2, *INK, filled=False)
        tx = x1 + 10
        if not self.value and not self.composing and not self.active:
            text.draw(placeholder, tx, self.y - 1, 22, SOFT)   # 비었으면 기본 이름을 옅게
            return
        if self.value:
            text.draw(self.value, tx, self.y - 1, 22, INK)
            tx += text.image(self.value, 22, INK).w
        if self.composing:
            text.draw(self.composing, tx, self.y - 1, 22, SOFT)
            tx += text.image(self.composing, 22, SOFT).w
        if self.active and int(self.t * 2) % 2 == 0:   # 깜빡이는 커서
            draw_rectangle(tx + 1, y1 + 7, tx + 2, y2 - 7, *INK, filled=True)
