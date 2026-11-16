"""유닛 그리기 화면. 준비 화면의 '유닛 추가하기' 를 누르면 그 위에 뜬다 (push_mode).

위에서부터
- 내 프리셋: 그려서 저장한 유닛. 누르면 그 그림·틀·체형이 종이에 올라와 이어 그리거나 고칠 수 있다.
  카드에 마우스를 올리면 드는 잉크가 뜨고, × 를 두 번 누르면 그 프리셋을 지운다
- 틀: 탱커(방패 기사) / 근접 딜러(검사) / 원거리 딜러(궁수) / 서포터(마법사)
- 잉크: 검정·빨강·초록·파랑 잉크병 + 지우개 (병 옆 숫자는 가진 잉크, 그려도 줄지 않는다) · 체형: 작은 / 보통 / 큰
- 종이 여러 장: 왼쪽 사람 종이, 그 옆에 무기마다 한 장 (원딜은 활·화살 두 장). 체형에 따라 종이·밑그림 크기가 바뀐다.
  틀·체형을 바꿔도 그리던 그림은 발 자리를 맞춰 옮겨 온다.
  들어오자마자 바로 그릴 수 있고, 붓질은 시작한 종이 안에서만 칠해진다. 커서 자리에 지금 붓 색·굵기의 점이 보인다.
  가진 잉크와 상관없이 어떤 색이든 마음껏 칠한다 (잉크는 내 유닛에서 놓을 때 따진다)
오른쪽: 되돌리기 / 다 지우기 / 저장하기(프리셋에 더하고 드는 잉크를 적어 둔다) / 닫기

키: 1~4 잉크, E 지우개, Ctrl+Z 되돌리기, ESC 닫기
"""
import numpy as np
from pico2d import (clear_canvas, update_canvas, get_events,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP, SDL_BUTTON_LEFT,
                    SDLK_ESCAPE, SDLK_1, SDLK_4, SDLK_e, SDLK_z)
from sdl2 import SDL_GetModState, KMOD_CTRL

import frames
import game_framework
import painter
import prepare_mode
import save_data
import text
import title_mode
import unit_art
import unit_cards
from assets import image
from live_image import LiveImage
from ui_button import Button

W, H = 1280, 720
INK = prepare_mode.INK
SOFT = (130, 110, 150)
TOAST_TIME = 1.8
FADE_IN = 0.18

# 줄마다 y (pico 좌표, 위가 큼)
PRESET_Y, FRAME_Y, INK_Y = 652, 554, 466
ROW_X = 220                     # 줄 내용이 시작하는 x
PRESET_GAP, MAX_PRESETS = 124, 8
FRAME_GAP = 216
INK_GAP = 120
BODY_X, BODY_GAP = 880, 100     # 체형 칸
# 종이들: 종이 칸(AREA) 가운데에 SHEET_GAP 간격으로 나란히, 아랫변을 맞춰서 (pico 좌표).
# 체형마다 종이 크기가 달라도 늘 칸 가운데에 온다
AREA_L, AREA_R, AREA_B, AREA_T = ROW_X - 10, 836, 26, 428
SHEET_GAP = 30
SIDE_X = 1040                   # 오른쪽 칸 가운데
SIDE_L, SIDE_R = 940, 1140      # 오른쪽 버튼 두 줄
TOOLS = painter.COLORS + (painter.ERASER,)
NAMES = {'black': '검정', 'red': '빨강', 'green': '초록', 'blue': '파랑'}


class Sheet:
    """종이 한 장: 칠한 내용(Paper) + 화면에 올린 텍스처 + 자리."""

    def __init__(self, label, guide, left, bottom, size):
        self.label, self.guide, self.left = label, guide, left
        self.w, self.h = size
        self.paper = painter.Paper(self.w, self.h)
        self.tex = LiveImage(self.w, self.h)
        self.paper.dirty = (0, 0, self.w, self.h)
        self.cx, self.cy = left + self.w / 2, bottom + self.h / 2
        self.top = bottom + self.h

    def local(self, mx, my, clamp=False):
        """화면 좌표 → 이 종이 좌표 (왼쪽 위 0,0). 밖이면 None (clamp 면 가장자리 너머로 조금까지)."""
        px, py = mx - self.left, self.top - my
        if clamp:
            return min(max(px, -1), self.w), min(max(py, -1), self.h)
        if 0 <= px < self.w and 0 <= py < self.h:
            return px, py
        return None

    def sync(self):
        if self.paper.dirty:
            x0, y0, x1, y1 = self.paper.dirty
            self.tex.upload(self.paper.rgba(self.paper.dirty), x0, y0)
            self.paper.dirty = None


panel = ink_wave = eraser_img = fade = toast_img = None
frame_imgs = {}
body_imgs = {}
ink_icons = {}
brush_tips = {}         # 도구 → 커서 자리에 보일 붓 점
buttons = []
sheets = []             # [사람 종이, 무기 종이 …]
edits = []              # 되돌리기 순서: 바꾼 종이 번호들 (한 번에 여러 장 바뀌면 (0, 1, …))
frame_id = frames.IDS[0]
body = 'medium'
tool = 'black'
picked = None           # 지금 종이에 올린 프리셋 id
painting = None         # 붓질 중인 종이 번호
deleter = None
toast = None
t = 0.0


# ---------------------------------------------------------------- 자리 계산
def preset_x(i):
    return ROW_X + 56 + PRESET_GAP * i


def frame_x(i):
    return ROW_X + 102 + FRAME_GAP * i


def ink_x(i):
    return ROW_X + 30 + INK_GAP * i


def body_x(i):
    return BODY_X + BODY_GAP * i


def sheet_at(mx, my):
    for i, s in enumerate(sheets):
        if s.local(mx, my):
            return i
    return None


def hit(x, y, w, h, mx, my):
    return abs(mx - x) <= w / 2 and abs(my - y) <= h / 2


def shown_units():
    units = save_data.current['units'] if save_data.current else []
    return units[-MAX_PRESETS:]


def preset_cards():
    return [(u, preset_x(i), PRESET_Y) for i, u in enumerate(shown_units())]


def owned():
    """잉크병 옆에 보일 남은 잉크 (내 유닛에 놓은 만큼 빠진 것)."""
    return save_data.ink_left(save_data.current) if save_data.current else {c: 0 for c in painter.COLORS}


def ink_used():
    return {c: painter.ink_for(n) for c, n in counts().items()}


def counts():
    return {c: sum(s.paper.count(c) for s in sheets) for c in painter.COLORS}


def build_sheets(keep=True):
    """지금 틀·체형의 종이들을 만든다. keep 이면 그리던 그림을 (발 자리를 맞춰) 새 종이로 옮긴다."""
    global sheets, edits
    f = frames.get(frame_id, body)
    specs = [('사람', f'guide_person_{frame_id}_{body}', f['size'])] + \
        [(g['name'], f'guide_gear_{frame_id}_{i}_{body}', g['size']) for i, g in enumerate(f['gear'])]
    old = sheets if keep else []
    total_w = sum(sz[0] for _, _, sz in specs) + SHEET_GAP * (len(specs) - 1)
    bottom = round((AREA_B + AREA_T) / 2 - max(sz[1] for _, _, sz in specs) / 2)
    new, x = [], round((AREA_L + AREA_R) / 2 - total_w / 2)
    for i, (label, guide, size) in enumerate(specs):
        s = Sheet(label, guide, x, bottom, size)
        if i < len(old) and not old[i].paper.is_empty():
            s.paper.load_rgba(frames.fit(old[i].paper.rgba(), *size))
            s.paper.history.clear()
        new.append(s)
        x += size[0] + SHEET_GAP
    sheets = new
    edits = []


def say(msg):
    global toast
    toast = (msg, TOAST_TIME)


def record(*which):
    edits.append(which)
    del edits[:-painter.MAX_UNDO * 2]


# ---------------------------------------------------------------- 행동
def pick_tool(name):
    global tool
    tool = name


def pick_frame(fid):
    global frame_id
    if fid != frame_id:
        frame_id = fid
        build_sheets()


def pick_body(name):
    global body
    if name != body:
        body = name
        build_sheets()


def pick_preset(unit):
    global picked, frame_id, body
    if unit.get('frame') not in frames.IDS:
        say('그림 파일을 찾을 수 없어요')
        return
    frame_id = unit['frame']
    body = unit.get('body', 'medium') if unit.get('body') in frames.BODIES else 'medium'
    build_sheets(keep=False)
    person, gears = unit_art.load(save_data.current['slot'], unit)
    for s, rgba in zip(sheets, [person] + gears):
        s.paper.load_rgba(rgba)
        s.paper.history.clear()
    picked = unit['id']


def save_unit():
    global picked
    if not save_data.current:
        return
    if all(s.paper.is_empty() for s in sheets):
        say('아직 아무것도 그리지 않았어요')
        return
    unit = save_data.add_unit(save_data.current, frame_id, counts(), ink_used(), body=body)
    slot = save_data.current['slot']
    sheets[0].paper.save_png(save_data.unit_path(slot, unit['id']))
    for i, s in enumerate(sheets[1:]):
        s.paper.save_png(save_data.gear_path(slot, unit['id'], group=i))
    save_data.save_current()
    clear_paper()
    say(f'{frames.BODY_NAMES[body]} {frames.get(frame_id)["name"]} 유닛을 프리셋에 저장했어요!')


def undo():
    while edits:
        which = edits.pop()
        if any([sheets[i].paper.undo() for i in which]):
            return
    say('되돌릴 게 없어요')


def clear_paper():
    global picked
    changed = [i for i, s in enumerate(sheets) if not s.paper.is_empty()]
    for i in changed:
        sheets[i].paper.clear()
    if changed:
        record(*changed)
    picked = None


def close():
    game_framework.pop_mode()


# ---------------------------------------------------------------- 모드
def init():
    global panel, ink_wave, eraser_img, fade, toast_img, frame_imgs, body_imgs, ink_icons
    global brush_tips, buttons, sheets, edits, tool, picked, painting, deleter, toast, t
    panel = image('draw', 'panel.png')
    ink_wave = image('draw', 'ink_wave.png')
    eraser_img = image('draw', 'eraser.png')
    fade = image('common', 'fade.png')
    toast_img = image('prepare', 'toast.png')
    frame_imgs = {(f, on): image('draw', f'frame_{f}{"_on" if on else ""}.png')
                  for f in frames.IDS for on in (False, True)}
    body_imgs = {(b, on): image('draw', f'body_{b}{"_on" if on else ""}.png')
                 for b in frames.BODIES for on in (False, True)}
    ink_icons = {c: image('prepare', f'ink_{c}.png') for c in painter.COLORS}
    if not brush_tips:
        brush_tips = {name: LiveImage(*tip.shape[1::-1], tip) for name, tip in
                      ((name, make_brush_tip(name)) for name in TOOLS)}
    sheets = []
    build_sheets(keep=False)
    # 오른쪽 두 칸: 위 줄 되돌리기·다 지우기, 아래 줄 저장하기·닫기
    buttons = [Button(x, y, f'button_{name}.png', f'button_{name}_hover.png', action, 0.3 * i, 'draw')
               for i, (name, x, y, action) in enumerate((
                   ('undo', SIDE_L, 270, undo), ('clear', SIDE_R, 270, clear_paper),
                   ('save', SIDE_L, 165, save_unit), ('close', SIDE_R, 165, close)))]
    tool = 'black'
    picked = painting = None
    deleter = unit_cards.Deleter()
    toast = None
    t = 0.0
    title_mode.move_mouse(title_mode.mouse)


def finish():
    save_data.save_current()


def pause():
    pass


def resume():
    pass


def move_mouse(pos):
    """종이 위에서는 붓자국 효과를 끈다 (그린 선과 헷갈리지 않게)."""
    if sheet_at(*pos) is not None or painting is not None:
        title_mode.mouse = pos
        title_mode.trail.last = None
    else:
        title_mode.move_mouse(pos)


def click(mx, my):
    global painting, picked
    if any(b.click(mx, my) for b in buttons):
        return
    gone = deleter.click(preset_cards(), mx, my)
    if gone == 'asked':
        say('한 번 더 누르면 이 프리셋을 지워요')
        return
    if gone is not None:
        if gone == picked:
            picked = None   # 종이에 올려 둔 그림은 그대로 둔다
        say('프리셋을 지웠어요')
        return
    for i, unit in enumerate(shown_units()):
        if unit_cards.hit(preset_x(i), PRESET_Y, mx, my):
            pick_preset(unit)
            return
    for i, fid in enumerate(frames.IDS):
        if hit(frame_x(i), FRAME_Y, 190, 80, mx, my):
            pick_frame(fid)
            return
    for i, name in enumerate(TOOLS):
        if hit(ink_x(i), INK_Y, 70, 60, mx, my):
            pick_tool(name)
            return
    for i, b in enumerate(frames.BODIES):
        if hit(body_x(i), INK_Y, 84, 42, mx, my):
            pick_body(b)
            return
    i = sheet_at(mx, my)
    if i is not None:
        painting = i
        sheets[i].paper.begin(*sheets[i].local(mx, my), tool)
        record(i)


def handle_events():
    global painting
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                close()
                return
            if SDLK_1 <= event.key <= SDLK_4:
                pick_tool(painter.COLORS[event.key - SDLK_1])
            elif event.key == SDLK_e:
                pick_tool(painter.ERASER)
            elif event.key == SDLK_z and SDL_GetModState() & KMOD_CTRL and painting is None:
                undo()
        elif event.type == SDL_MOUSEMOTION:
            mx, my = title_mode.to_canvas(event)
            move_mouse((mx, my))
            deleter.move(preset_cards(), mx, my)
            for b in buttons:
                b.mouse_move(mx, my)
            if painting is not None:
                # 종이 밖으로 나가도 그 종이 가장자리까지는 이어 칠한다 (다른 종이로 넘어가지 않는다)
                sheets[painting].paper.drag(*sheets[painting].local(mx, my, clamp=True), tool)
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            if t > FADE_IN:
                click(*title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEBUTTONUP and event.button == SDL_BUTTON_LEFT:
            if painting is not None:
                sheets[painting].paper.end()
                painting = None


def update():
    global t, toast
    dt = game_framework.frame_time
    t += dt
    for b in buttons:
        b.update()
    title_mode.trail.update()
    if toast:
        toast = (toast[0], toast[1] - dt) if toast[1] > dt else None
    for s in sheets:
        s.sync()


# ---------------------------------------------------------------- 그리기
def draw_presets():
    text.draw('내 프리셋', 46, PRESET_Y, 30, INK)
    units = shown_units()
    if not units:
        unit_cards.draw_empty(preset_x(0), PRESET_Y)
        text.draw('그려서 저장하면 여기에 생겨요', preset_x(0) + 76, PRESET_Y, 26, (150, 128, 170))
        return
    for i, unit in enumerate(units):
        unit_cards.draw(unit, preset_x(i), PRESET_Y, on=unit['id'] == picked, delete=deleter.state(unit))


def draw_frames():
    text.draw('틀', 46, FRAME_Y, 30, INK)
    for i, fid in enumerate(frames.IDS):
        frame_imgs[(fid, fid == frame_id)].draw(frame_x(i), FRAME_Y)


def draw_inks():
    text.draw('잉크', 46, INK_Y, 30, INK)
    have = owned()
    for i, name in enumerate(TOOLS):
        x = ink_x(i)
        if name == tool:
            ink_wave.draw(x + 2, INK_Y - 32)   # 고른 병 바로 아래 펜 밑줄
        bob = 3 if name == tool else 0
        if name == painter.ERASER:
            eraser_img.draw(x, INK_Y + bob, 48, 48)
            continue
        ink_icons[name].draw(x, INK_Y + bob, 42, 48)
        text.draw(str(have.get(name, 0)), x + 26, INK_Y - 2, 28, INK)
    text.draw('체형', BODY_X - 96, INK_Y, 26, INK)
    for i, b in enumerate(frames.BODIES):
        body_imgs[(b, b == body)].draw(body_x(i), INK_Y)


def make_brush_tip(name):
    """커서(펜촉) 위에 보일 붓 점 (RGBA): 그 색 점(흰 테두리) + 옅은 같은 색 고리. 지우개는 지우는 크기만 한 흰 동그라미."""
    if name == painter.ERASER:
        r, ring_r, fill, ring = painter.ERASER_R, painter.ERASER_R, (255, 255, 255, 210), (150, 128, 170, 230)
    else:
        r, ring_r, fill, ring = painter.BRUSH_R + 2, painter.BRUSH_R + 8, painter.RGB[name] + (255,), painter.RGB[name] + (150,)
    size = int(ring_r * 2 + 6)
    c = size / 2
    yy, xx = np.mgrid[0:size, 0:size] + 0.5
    d = np.hypot(xx - c, yy - c)
    out = np.zeros((size, size, 4), np.uint8)
    out[..., :3] = ring[:3]
    out[..., 3] = (np.clip(1.4 - abs(d - ring_r) / 1.2, 0, 1) * ring[3]).astype(np.uint8)   # 부드러운 테두리
    a = (np.clip((r - 1 if name == painter.ERASER else r + 0.5) - d, 0, 1) * fill[3]).astype(np.uint8)
    if name != painter.ERASER:   # 점 둘레 흰 테두리 (펜촉·그림 위에서도 잘 보이게)
        rim = (np.clip(r + 2 - d, 0, 1) * 255).astype(np.uint8)
        out[rim > out[..., 3], :3] = 255
        out[..., 3] = np.maximum(out[..., 3], rim)
    keep = a > 0
    out[keep, :3] = fill[:3]
    out[..., 3] = np.maximum(out[..., 3], a)
    return out


def draw_brush_tip():
    mx, my = title_mode.mouse
    if sheet_at(mx, my) is not None:
        brush_tips[tool].draw(round(mx), round(my))


def draw_papers():
    for s in sheets:
        image('draw', f'paper_{s.w}x{s.h}.png').draw(s.cx, s.cy)
        image('draw', s.guide + '.png').draw(s.cx, s.cy)
        s.tex.draw(s.cx, s.cy)
        text.draw(s.label, s.left + 8, s.top - 16, 20, (170, 154, 186))


def draw_side():
    for b in buttons:
        b.draw()
    used = ink_used()
    lines = [f'{NAMES[c]} {used[c]}' for c in painter.COLORS if used[c]]
    f = frames.get(frame_id, body)
    text.draw(f'{frames.BODY_NAMES[body]} {f["name"]}  ·  검정 → {f["stat"]} ↑  ·  색 → 원소', SIDE_X, 420, 20, SOFT, 'c')
    text.draw('이 그림에 드는 잉크', SIDE_X, 384, 24, INK, 'c')
    text.draw('  ·  '.join(lines) if lines else '아직 없음', SIDE_X, 354, 24, SOFT, 'c')
    text.draw('Ctrl+Z 로도 되돌려요', SIDE_X, 92, 20, (150, 128, 170), 'c')


def draw_toast():
    if not toast:
        return
    msg, left = toast
    a = min(1.0, left / 0.4, (TOAST_TIME - left) / 0.15)
    x, y = (sheets[0].left + sheets[-1].left + sheets[-1].w) / 2, (AREA_B + AREA_T) / 2
    toast_img.opacify(a)
    toast_img.draw(x, y)
    toast_img.opacify(1)
    text.draw(msg, x, y + 2, 28, INK, 'c', alpha=a)


def draw():
    clear_canvas()
    prepare_mode.draw_scene()
    panel.draw(W / 2, H / 2, W - 16, H - 12)
    draw_presets()
    draw_frames()
    draw_inks()
    draw_papers()
    draw_side()
    unit_cards.draw_tip(deleter.hover, preset_cards())   # 마우스를 올린 카드: 드는 잉크
    draw_toast()
    if t < FADE_IN:
        fade.opacify(0.5 * (1 - t / FADE_IN))
        fade.draw(W / 2, H / 2, W, H)
        fade.opacify(1)
    title_mode.draw_cursor()
    draw_brush_tip()   # 펜촉 위에: 지금 칠할 색이 펜 끝에 묻은 듯
    update_canvas()
