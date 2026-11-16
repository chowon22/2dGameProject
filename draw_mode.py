"""유닛 그리기 화면. 준비 화면의 '유닛 추가하기' 를 누르면 그 위에 뜬다 (push_mode).

위에서부터
- 내 프리셋: 그려서 저장한 유닛. 누르면 그 그림과 틀이 종이에 올라와 이어 그리거나 고칠 수 있다
- 틀: 탱커 / 근접 딜러 / 원거리 딜러 / 서포터. 고르면 종이에 흐릿한 틀 실루엣이 깔린다
- 잉크: 검정·빨강·초록·파랑 잉크병 + 지우개. 병 옆 숫자는 가진 잉크 (그려도 줄지 않는다)
- 종이: 들어오자마자 바로 그릴 수 있다. 한 그림에 가진 잉크보다 많이는 칠해지지 않는다 (PRD 9.1 #6)
오른쪽: 저장하기(프리셋에 더하고 이 유닛에 드는 잉크를 적어 둔다 — 가진 잉크는 그대로) / 다 지우기 / 닫기

키: 1~4 잉크, E 지우개, ESC 닫기
"""
import numpy as np
from PIL import Image as PILImage
from pico2d import (clear_canvas, update_canvas, get_events,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP, SDL_BUTTON_LEFT,
                    SDLK_ESCAPE, SDLK_1, SDLK_4, SDLK_e)

import frames
import game_framework
import painter
import prepare_mode
import save_data
import text
import title_mode
from assets import image
from live_image import LiveImage
from ui_button import Button

W, H = 1280, 720
INK = prepare_mode.INK
TOAST_TIME = 1.8
FADE_IN = 0.18

# 줄마다 y (pico 좌표, 위가 큼)
PRESET_Y, FRAME_Y, INK_Y = 652, 554, 466
ROW_X = 220                     # 줄 내용이 시작하는 x
PRESET_GAP, MAX_PRESETS = 124, 8
THUMB_W, THUMB_H = 84, 52       # 프리셋 카드 안 그림 칸
FRAME_GAP = 216
INK_GAP = 120
# 종이: 가운데 (PAPER_X, PAPER_Y), 실제로 칠하는 곳은 frames.PAPER_W x PAPER_H
PAPER_X, PAPER_Y = 520, 222
PAPER_L = PAPER_X - frames.PAPER_W // 2
PAPER_T = PAPER_Y + frames.PAPER_H // 2     # 종이 윗변 (pico y)
SIDE_X = 1080
TOOLS = painter.COLORS + (painter.ERASER,)

panel = paper_img = ink_ring = eraser_img = fade = toast_img = None
card_imgs = {}
frame_imgs = {}
ink_icons = {}
silhouettes = {}
buttons = []
paper = None
paper_tex = None
thumbs = {}             # 유닛 id → 썸네일 Image
frame_id = frames.IDS[0]
tool = 'black'
picked = None           # 지금 종이에 올린 프리셋 id
painting = False
toast = None
t = 0.0


# ---------------------------------------------------------------- 자리 계산
def preset_x(i):
    return ROW_X + 56 + PRESET_GAP * i


def frame_x(i):
    return ROW_X + 102 + FRAME_GAP * i


def ink_x(i):
    return ROW_X + 30 + INK_GAP * i


def to_paper(mx, my):
    """화면 좌표 → 종이 좌표 (왼쪽 위 0,0). 종이 밖이면 None."""
    px, py = mx - PAPER_L, PAPER_T - my
    if 0 <= px < frames.PAPER_W and 0 <= py < frames.PAPER_H:
        return px, py
    return None


def hit(x, y, w, h, mx, my):
    return abs(mx - x) <= w / 2 and abs(my - y) <= h / 2


def shown_units():
    units = save_data.current['units'] if save_data.current else []
    return units[-MAX_PRESETS:]


def owned():
    return save_data.current['ink'] if save_data.current else {c: 0 for c in painter.COLORS}


def say(msg):
    global toast
    toast = (msg, TOAST_TIME)


# ---------------------------------------------------------------- 행동
def pick_tool(name):
    global tool
    if name != painter.ERASER and owned().get(name, 0) <= 0:
        say('아직 없는 색이에요.  몬스터에게서 되찾아 와요!')
        return
    tool = name


def pick_frame(fid):
    global frame_id
    frame_id = fid


def pick_preset(unit):
    global picked, frame_id
    path = save_data.unit_path(save_data.current['slot'], unit['id'])
    try:
        paper.load_png(path)
    except OSError:
        say('그림 파일을 찾을 수 없어요')
        return
    picked = unit['id']
    if unit.get('frame') in frames.IDS:
        frame_id = unit['frame']


def save_unit():
    global picked
    if not save_data.current:
        return
    if paper.is_empty():
        say('아직 아무것도 그리지 않았어요')
        return
    used = paper.ink_used()
    unit = save_data.add_unit(save_data.current, frame_id, paper.counts_dict(), used)
    paper.save_png(save_data.unit_path(save_data.current['slot'], unit['id']))
    save_data.save_current()
    paper.clear()
    picked = None
    say(f'{frames.get(frame_id)["name"]} 유닛을 프리셋에 저장했어요!')


def clear_paper():
    global picked
    paper.clear()
    picked = None


def close():
    game_framework.pop_mode()


# ---------------------------------------------------------------- 모드
def init():
    global panel, paper_img, ink_ring, eraser_img, fade, toast_img, card_imgs, frame_imgs, ink_icons
    global silhouettes, buttons, paper, paper_tex, thumbs, tool, picked, painting, toast, t
    panel = image('draw', 'panel.png')
    paper_img = image('draw', 'paper.png')
    ink_ring = image('draw', 'ink_ring.png')
    eraser_img = image('draw', 'eraser.png')
    fade = image('common', 'fade.png')
    toast_img = image('prepare', 'toast.png')
    card_imgs = {s: image('draw', f'card{s}.png') for s in ('', '_on', '_empty')}
    frame_imgs = {(f, on): image('draw', f'frame_{f}{"_on" if on else ""}.png')
                  for f in frames.IDS for on in (False, True)}
    ink_icons = {c: image('prepare', f'ink_{c}.png') for c in painter.COLORS}
    if not silhouettes:
        silhouettes = {f: LiveImage(frames.PAPER_W, frames.PAPER_H, frames.silhouette(f)) for f in frames.IDS}
    paper = painter.Paper(frames.PAPER_W, frames.PAPER_H)
    if paper_tex is None:
        paper_tex = LiveImage(frames.PAPER_W, frames.PAPER_H)
    paper.dirty = (0, 0, paper.w, paper.h)
    buttons = [Button(SIDE_X, y, f'button_{name}.png', f'button_{name}_hover.png', action, 0.3 * i, 'draw')
               for i, (name, y, action) in enumerate((('save', 300, save_unit), ('clear', 200, clear_paper),
                                                      ('close', 100, close)))]
    thumbs = {}
    tool = 'black'
    picked = None
    painting = False
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
    if to_paper(*pos):
        title_mode.mouse = pos
        title_mode.trail.last = None
    else:
        title_mode.move_mouse(pos)


def click(mx, my):
    global painting
    if any(b.click(mx, my) for b in buttons):
        return
    for i, unit in enumerate(shown_units()):
        if hit(preset_x(i), PRESET_Y, 100, 80, mx, my):
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
    p = to_paper(mx, my)
    if p:
        painting = True
        paper.begin(*p, tool, owned())
        if paper.blocked and tool != painter.ERASER:
            say('잉크가 모자라요')


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
        elif event.type == SDL_MOUSEMOTION:
            mx, my = title_mode.to_canvas(event)
            move_mouse((mx, my))
            for b in buttons:
                b.mouse_move(mx, my)
            if painting:
                was = paper.blocked
                # 종이 밖으로 나가도 가장자리까지는 이어 칠한다
                px = min(max(mx - PAPER_L, -1), frames.PAPER_W)
                py = min(max(PAPER_T - my, -1), frames.PAPER_H)
                paper.drag(px, py, tool, owned())
                if paper.blocked and not was and tool != painter.ERASER:
                    say('잉크가 모자라요')
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            if t > FADE_IN:
                click(*title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEBUTTONUP and event.button == SDL_BUTTON_LEFT:
            if painting:
                paper.end()
                painting = False


def update():
    global t, toast
    dt = game_framework.frame_time
    t += dt
    for b in buttons:
        b.update()
    title_mode.trail.update()
    if toast:
        toast = (toast[0], toast[1] - dt) if toast[1] > dt else None
    if paper.dirty:
        x0, y0, x1, y1 = paper.dirty
        paper_tex.upload(paper.rgba(paper.dirty), x0, y0)
        paper.dirty = None


# ---------------------------------------------------------------- 그리기
def make_thumb(path):
    """그린 부분만 잘라 카드 칸에 맞게 줄인 썸네일."""
    img = PILImage.open(path).convert('RGBA')
    box = img.getbbox()
    if not box:
        return None
    img = img.crop(box)
    k = min(THUMB_W / img.width, THUMB_H / img.height, 1.0)
    img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), PILImage.LANCZOS)
    return LiveImage(img.width, img.height, np.asarray(img))


def thumb(unit):
    if unit['id'] not in thumbs:
        try:
            thumbs[unit['id']] = make_thumb(save_data.unit_path(save_data.current['slot'], unit['id']))
        except OSError:
            thumbs[unit['id']] = None
    return thumbs[unit['id']]


def draw_presets():
    text.draw('내 프리셋', 46, PRESET_Y, 30, INK)
    units = shown_units()
    if not units:
        card_imgs['_empty'].draw(preset_x(0), PRESET_Y)
        text.draw('그려서 저장하면 여기에 생겨요', preset_x(0) + 76, PRESET_Y, 26, (150, 128, 170))
        return
    for i, unit in enumerate(units):
        x = preset_x(i)
        card_imgs['_on' if unit['id'] == picked else ''].draw(x, PRESET_Y)
        img = thumb(unit)
        if img:
            img.draw(x, PRESET_Y + 8)
        name = frames.get(unit['frame'])['name'] if unit.get('frame') in frames.IDS else ''
        text.draw(name, x, PRESET_Y - 27, 17, INK, 'c')
        # 이 유닛에 드는 잉크: 카드 안 왼쪽 위에 작은 잉크병 딱지
        cost = sum(unit.get('ink', {}).values())
        ink_icons['black'].draw(x - 36, PRESET_Y + 27, 15, 17)
        text.draw(str(cost), x - 27, PRESET_Y + 26, 17, INK)


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
            ink_ring.draw(x + 18, INK_Y - 26)
        bob = 3 if name == tool else 0
        if name == painter.ERASER:
            eraser_img.draw(x, INK_Y + bob, 48, 48)
            continue
        icon = ink_icons[name]
        if owned().get(name, 0) <= 0:
            icon.opacify(0.35)
        icon.draw(x, INK_Y + bob, 42, 48)
        icon.opacify(1)
        text.draw(str(have.get(name, 0)), x + 26, INK_Y - 2, 28, INK)
    f = frames.get(frame_id)
    text.draw(f'{f["name"]}:  검정 → {f["stat"]} ↑  ·  색 → 원소', ink_x(len(TOOLS)) - 10, INK_Y, 22, (130, 110, 150))


def draw_paper():
    paper_img.draw(PAPER_X, PAPER_Y)
    silhouettes[frame_id].draw(PAPER_X, PAPER_Y)
    paper_tex.draw(PAPER_X, PAPER_Y)


def draw_side():
    for b in buttons:
        b.draw()
    used = paper.ink_used()
    names = {'black': '검정', 'red': '빨강', 'green': '초록', 'blue': '파랑'}
    lines = [f'{names[c]} {used[c]}' for c in painter.COLORS if used[c]]
    text.draw('이 그림에 드는 잉크', SIDE_X, 412, 24, INK, 'c')
    text.draw('  ·  '.join(lines) if lines else '아직 없음', SIDE_X, 380, 24, (130, 110, 150), 'c')


def draw_toast():
    if not toast:
        return
    msg, left = toast
    a = min(1.0, left / 0.4, (TOAST_TIME - left) / 0.15)
    toast_img.opacify(a)
    toast_img.draw(PAPER_X, PAPER_Y)
    toast_img.opacify(1)
    text.draw(msg, PAPER_X, PAPER_Y + 2, 28, INK, 'c', alpha=a)


def draw():
    clear_canvas()
    prepare_mode.draw_scene()
    panel.draw(W / 2, H / 2, W - 16, H - 12)
    draw_presets()
    draw_frames()
    draw_inks()
    draw_paper()
    draw_side()
    draw_toast()
    if t < FADE_IN:
        fade.opacify(0.5 * (1 - t / FADE_IN))
        fade.draw(W / 2, H / 2, W, H)
        fade.opacify(1)
    title_mode.draw_cursor()
    update_canvas()
