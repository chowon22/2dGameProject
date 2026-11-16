"""전투 화면 (PRD 6장). 출전 준비(units_mode)에서 시작! 을 누르면 뜬다 (push_mode, stage_id 를 정해서).

- 왼쪽에 내 유닛(놓은 자리 그대로, 틀에 맞춰 숨쉬는 그림), 오른쪽에 그 스테이지 몬스터
- 내 차례: 앞줄부터 아군이 하나씩 (발밑이 노랗게) — 적을 누르면 달려가 휘둘러 색을 흡수(피해).
  서포터는 아군을 누르면 치료 + 다음 공격 힘 보태기, 적을 누르면 약하게 공격. 넘기기로 건너뛸 수 있다
- 적 차례: 적이 하나씩 아군을 공격 (탱커가 공격을 끌어온다)
- 체력바 대신 그림이 흐려진다 (PRD 1.4: 그림이 곧 체력): 맞으면 바로 반투명, 체력이 줄수록 더 흐리게. 발밑에 남은 체력 숫자
- 끝: 승리면 되찾은 잉크를 받고 다음 스테이지가 열린다. 돌아가기 → 스테이지 고르기
- 도망가기: 아무것도 받지 않고 스테이지 고르기로
"""
import math

from pico2d import (clear_canvas, update_canvas, get_events, SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION,
                    SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT, SDLK_ESCAPE)

import battle
import game_framework
import prepare_mode
import save_data
import stages
import stats
import text
import title_mode
import unit_cards
import unit_rig
from assets import image
from ui_button import Button

W, H = 1280, 720
INK = prepare_mode.INK
SOFT = (150, 128, 170)
NAMES = {'black': '검정', 'red': '빨강', 'green': '초록', 'blue': '파랑'}
FRONT_X, BACK_X = 470, 290                 # 아군 앞줄·뒷줄 x (적은 화면 가운데를 기준으로 뒤집는다)
LANE_Y = (236, 170, 104)                   # 줄(먼 쪽 → 가까운 쪽)마다 발 y
LANE_SKEW = (64, 0, -64)                   # 먼 줄은 오른쪽으로 (체력 숫자가 덜 겹치게)
UNIT_SCALE = 0.3
MONSTER_SCALE = 0.72
ACT_TIME, HIT_AT = 0.62, 0.32              # 공격 한 번 걸리는 시간, 맞는 순간
LUNGE = 0.42                               # 상대 쪽으로 다가가는 정도
FADE_IN = 0.3
HURT_MIN = stats.HURT_MIN                  # 쓰러질 때 여기서부터 사라진다
HIT_FLASH = 0.3                            # 맞는 순간 흔들리며 흐려지는 시간

stage_id = None
battle_state = None                        # battle.Battle
views = []                                 # 화면에 그릴 전투원: {'f', 'x', 'y', 'rig' | 'img', 'k', 'name'}
anim = None                                # 진행 중인 행동 연출
enemy_queue = []
enemy_turn = False                         # 적 차례가 시작되어 적들이 차례로 움직이는 중
popups = []                                # [글씨, x, y, 남은 시간, 색]
buttons = []
end_button = None
result = None                              # None / 'win' / 'lose'
reward = {}
hover = None
t = 0.0
bg = {}


# ---------------------------------------------------------------- 자리
def spot(side, slot):
    lane = slot % 3
    x = (FRONT_X if slot < 3 else BACK_X) + LANE_SKEW[lane]
    return (x if side == 'ally' else W - x), LANE_Y[lane]


def view_of(f):
    return next(v for v in views if v['f'] is f)


def view_at(mx, my):
    best = None
    for v in views:
        if not v['f'].alive:
            continue
        if abs(mx - v['x']) <= 52 and v['y'] - 10 <= my <= v['y'] + 110:
            if best is None or v['y'] < best['y']:   # 가까운 줄(아래)이 앞
                best = v
    return best


def label(v):
    return v['name']


# ---------------------------------------------------------------- 시작
def make_views():
    global views
    views = []
    data = save_data.current
    allies, enemies = [], []
    for slot, uid in enumerate(data['party']):
        unit = save_data.find_unit(data, uid) if uid is not None else None
        if not unit:
            continue
        f = battle.Fighter('ally', slot, stats.unit_stats(unit), unit)
        frac = save_data.hp_list(data)[slot]          # 지난 전투에서 다친 채로 (치료 안 했으면)
        f.hp = 0 if frac <= 0 else max(1, round(f.max_hp * frac))
        allies.append(f)
        x, y = spot('ally', slot)
        views.append({'f': f, 'x': x, 'y': y, 'rig': unit_rig.rig(unit, UNIT_SCALE), 'name': unit_cards.label(unit),
                      'dead_t': 0.0})
    for e in stages.enemies(stage_id):
        f = battle.Fighter('enemy', e['slot'], e, e)
        enemies.append(f)
        x, y = spot('enemy', e['slot'])
        views.append({'f': f, 'x': x, 'y': y, 'img': image(*e['image']), 'k': MONSTER_SCALE * e['scale'],
                      'name': e['name'], 'dead_t': 0.0})
    return allies, enemies


def init():
    global battle_state, anim, enemy_queue, enemy_turn, popups, buttons, end_button, result, reward, hover, t, bg
    bg = {name: image('prepare', name + '.png') for name in ('sky', 'far', 'mid', 'ground', 'shadow')}
    allies, enemies = make_views()
    battle_state = battle.Battle(allies, enemies)
    anim, enemy_queue, enemy_turn, popups = None, [], False, []
    buttons = [Button(930, 52, 'button_skip.png', 'button_skip_hover.png', skip, 0.0, 'world'),
               Button(1130, 52, 'button_flee.png', 'button_flee_hover.png', leave, 0.4, 'world')]
    end_button = Button(W / 2, 300, 'button_return.png', 'button_return_hover.png', leave, 0.0, 'world')
    result, reward, hover = None, {}, None
    t = 0.0
    title_mode.move_mouse(title_mode.mouse)


def finish():
    save_data.save_current()


def pause():
    pass


def resume():
    pass


# ---------------------------------------------------------------- 행동
def save_hp():
    """아군 남은 체력을 세이브의 자리별 체력에 적는다 (다친 상태가 다음 전투까지 이어진다)."""
    hp = save_data.hp_list(save_data.current)
    for f in battle_state.allies:
        hp[f.slot] = f.hp / f.max_hp
    save_data.save_current()


def leave():
    """스테이지 고르기로 (전투 화면과 출전 준비 화면을 함께 닫는다). 도망쳐도 다친 건 그대로."""
    save_hp()
    game_framework.pop_mode()
    game_framework.pop_mode()


def skip():
    if result or anim or battle_state.turn != 'player':
        return
    actor = battle_state.actor()
    if actor:
        battle_state.skip(actor)
        after_action()


def start(kind, actor, target):
    global anim
    anim = {'kind': kind, 'actor': actor, 'target': target, 't': 0.0, 'done': False}


def click(mx, my):
    if result:
        end_button.click(mx, my)
        return
    if any(b.click(mx, my) for b in buttons):
        return
    if anim or battle_state.turn != 'player':
        return
    actor = battle_state.actor()
    v = view_at(mx, my)
    if not actor or not v:
        return
    f = v['f']
    if f.side == 'enemy':
        start('attack', actor, f)
    elif actor.role == 'support':
        start('support', actor, f)


def apply_hit():
    """행동 연출 한가운데: 실제로 피해·치료를 넣고 숫자를 띄운다."""
    a = anim
    tv = view_of(a['target'])
    if a['kind'] == 'support':
        healed = battle_state.support(a['actor'], a['target'])
        popups.append([f'+{healed}  힘 보태기!', tv['x'], tv['y'] + 120, 1.0, (70, 150, 100)])
        return
    if a['kind'] == 'attack':
        dmg, mul = battle_state.attack(a['actor'], a['target'])
    else:
        dmg, mul = battle_state.enemy_hit(a['actor'], a['target'])
    tv['shake'] = HIT_FLASH
    popups.append([f'-{dmg}', tv['x'], tv['y'] + 110, 1.0, (210, 70, 80)])
    if mul > 1:
        popups.append(['상성이 좋아요!', tv['x'], tv['y'] + 140, 1.0, (220, 140, 40)])
    elif mul < 1:
        popups.append(['상성이 나빠요…', tv['x'], tv['y'] + 140, 1.0, SOFT])


def after_action():
    """행동이 끝나면: 끝났는지, 적 차례로 넘어갈지, 다음 적 행동."""
    global result, reward, enemy_queue, enemy_turn
    res = battle_state.result()
    if res:
        result = res
        if res == 'win':
            reward = stages.clear(save_data.current, stage_id)
        save_hp()
        return
    if battle_state.turn == 'enemy':
        if not enemy_turn:   # 적 차례가 막 시작됨: 이번 차례에 움직일 적들
            enemy_turn = True
            enemy_queue = [e for e, _ in battle_state.enemy_plan()]
        next_enemy()


def next_enemy():
    global enemy_queue, enemy_turn
    while enemy_queue:
        e = enemy_queue.pop(0)
        if e.alive:
            target = battle_state.pick_target()
            if target:
                start('enemy', e, target)
                return
    enemy_turn = False   # 다 움직였으면 내 차례로
    battle_state.end_enemy_turn()


# ---------------------------------------------------------------- 모드
def handle_events():
    global hover
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            leave()
            return
        elif event.type == SDL_MOUSEMOTION:
            mx, my = title_mode.to_canvas(event)
            title_mode.move_mouse((mx, my))
            for b in buttons + [end_button]:
                b.mouse_move(mx, my)
            hover = view_at(mx, my)
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT and t > FADE_IN:
            click(*title_mode.to_canvas(event))


def update():
    global t, anim, popups
    dt = game_framework.frame_time
    t += dt
    for b in buttons + [end_button]:
        b.update()
    title_mode.trail.update()
    for v in views:
        v['shake'] = max(0.0, v.get('shake', 0.0) - dt)
        if not v['f'].alive:
            v['dead_t'] += dt
    for p in popups:
        p[2] += 40 * dt
        p[3] -= dt
    popups = [p for p in popups if p[3] > 0]
    if anim:
        anim['t'] += dt
        if anim['t'] >= HIT_AT and not anim['done']:
            anim['done'] = True
            apply_hit()
        if anim['t'] >= ACT_TIME:
            anim = None
            after_action()


# ---------------------------------------------------------------- 그리기
def draw_background():
    bg['sky'].draw(W / 2, H / 2)
    bg['far'].draw(W / 2, H / 2 + 80)
    bg['mid'].draw(W / 2, H / 2 + 80)
    bg['ground'].draw(W / 2, 135, W, 270)   # 땅을 넓게: 윗선이 y 240 쯤


def offset(v):
    """행동 연출 중인 전투원: 상대 쪽으로 다가갔다 돌아오기 / 맞으면 흔들림."""
    dx = dy = 0.0
    if anim and anim['actor'] is v['f'] and anim['kind'] != 'support':
        tv = view_of(anim['target'])
        k = math.sin(min(1.0, anim['t'] / ACT_TIME) * math.pi) * LUNGE
        dx, dy = (tv['x'] - v['x']) * k, (tv['y'] - v['y']) * k
    if v.get('shake'):
        dx += math.sin(v['shake'] * 60) * 6
    return dx, dy


def opacity(v):
    """그림이 곧 체력 (PRD 1.4): 한 번이라도 맞으면 바로 반투명해지고, 체력이 줄수록 더 흐려진다.
    맞는 순간에는 잠깐 더 흐려졌다가 돌아오고, 쓰러지면 사라진다."""
    f = v['f']
    if not f.alive:
        return max(0.0, HURT_MIN - v['dead_t'] * 0.5)
    a = stats.hurt_alpha(f.hp / f.max_hp)
    if v.get('shake'):
        a *= 0.45 + 0.55 * (1 - v['shake'] / HIT_FLASH)   # 맞는 순간 확 흐려졌다가 돌아옴
    return a


def draw_fighter(v):
    f = v['f']
    a = opacity(v)
    if a <= 0:
        return
    dx, dy = offset(v)
    x, y = v['x'] + dx, v['y'] + dy
    bg['shadow'].draw(x, y - 2, 90, 16)
    actor = battle_state.actor() if not anim and not result else None
    if f is actor or (hover is v and not anim and not result and actor and
                      (f.side == 'enemy' or actor.role == 'support')):
        image('draw', 'spot_on.png').draw(x, y)
    if 'rig' in v:
        if v['rig']:
            if anim and anim['actor'] is f and anim['kind'] == 'attack':
                v['rig'].draw(x, y, 'attack', anim['t'] / ACT_TIME, a)
            else:
                v['rig'].draw(x, y, 'idle', t * 2 + f.slot, a)
    else:
        img, k = v['img'], v['k']
        img.opacify(a)
        img.composite_draw(0.04 * math.sin(t * 2 + f.slot), 'h', x, y + img.h * k / 2 + 3 * math.sin(t * 2.4 + f.slot),
                           img.w * k, img.h * k)
        img.opacify(1)
    if f.alive:
        elem = stats.ELEMENT_NAMES.get(f.element) if f.element else ''
        text.draw(f'{f.hp}/{f.max_hp}' + (f'  {elem}' if elem else ''), x, y - 18, 18, INK, 'c')
    if f is actor:
        text.draw('▼', x, y + 128 + 4 * math.sin(t * 5), 24, (214, 160, 52), 'c')


def draw_hud():
    st = stages.stage(stage_id)
    text.draw(f'{stage_id}  {st["name"]}', 40, 680, 30, INK)
    text.draw(f'{battle_state.round}번째 차례', 40, 646, 22, SOFT)
    if result:
        return
    actor = battle_state.actor()
    if battle_state.turn == 'enemy' or (anim and anim['kind'] == 'enemy'):
        msg = '적 차례…'
    elif actor:
        v = view_of(actor)
        msg = f'{label(v)} 차례  —  ' + ('치료할 아군이나 공격할 적을 눌러요' if actor.role == 'support'
                                        else '공격할 적을 눌러요')
    else:
        msg = ''
    text.draw(msg, W / 2, 680, 28, INK, 'c')


def draw_result():
    if not result:
        return
    fade = image('common', 'fade.png')
    fade.opacify(0.35)
    fade.draw(W / 2, H / 2, W, H)
    fade.opacify(1)
    image('world', 'result.png').draw(W / 2, 400)
    if result == 'win':
        text.draw('이겼어요!', W / 2, 470, 44, INK, 'c')
        got = '  ·  '.join(f'{NAMES.get(c, c)} +{n}' for c, n in reward.items())
        text.draw('되찾은 잉크', W / 2, 410, 24, SOFT, 'c')
        text.draw(got or '없음', W / 2, 374, 30, INK, 'c')
    else:
        text.draw('졌어요…', W / 2, 470, 44, INK, 'c')
        text.draw('그림을 더 칠하거나 자리를 바꿔서 다시 와요', W / 2, 410, 26, SOFT, 'c')
        text.draw('다친 유닛은 내 유닛에서 치료해요', W / 2, 374, 22, SOFT, 'c')
    end_button.draw()


def draw():
    clear_canvas()
    draw_background()
    for v in sorted(views, key=lambda v: -v['y']):   # 먼 줄(위)부터
        draw_fighter(v)
    for msg, x, y, left, col in popups:
        text.draw(msg, x, y, 30, col, 'c', alpha=min(1.0, left * 2))
    draw_hud()
    if not result:
        for b in buttons:
            b.draw()
    draw_result()
    if t < FADE_IN:
        f = image('common', 'fade.png')
        f.opacify(1 - t / FADE_IN)
        f.draw(W / 2, H / 2, W, H)
        f.opacify(1)
    title_mode.draw_cursor()
    update_canvas()
