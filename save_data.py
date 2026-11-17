"""세이브 파일. 슬롯마다 data/saves/slot_<n>.json 하나 (PRD 9.2 #11: 데이터는 JSON으로 분리).

pico2d 와 무관한 순수 로직이라 따로 테스트할 수 있다 (tests/test_save_data.py).

- new_game(slot): 새 세이브를 만들어 저장하고 지금 슬롯으로 고른다
- load(slot) / summary(slot): 불러오기 / 선택 화면에 보일 요약 (없으면 None)
- save_current(): 지금 슬롯을 저장 (플레이 시간을 더한다)
- delete(slot): 지우기 (그 슬롯의 유닛 그림도 함께)
- add_unit(data, frame, counts, ink_used): 그린 유닛을 프리셋으로 적는다 (드는 잉크만 기록, 가진 잉크는 그대로). 그림은 unit_path() 에 저장
- delete_unit(data, id): 프리셋 지우기 (그림 파일도, 내 유닛에 고른 것도 함께)
- party_hp: 자리마다 남은 체력 비율. 전투에서 다친 상태가 이어지고, 치료(heal)해야 다시 찬다
- party: 내 유닛 화면에서 필드 자리(6칸: 앞줄 3 + 뒷줄 3)마다 놓은 프리셋 id. 같은 프리셋을 여러 번 놓을 수 있다.
  드는 잉크 합이 가진 잉크를 넘지 않게 can_place() 로 막는다
"""
import glob
import json
import math
import os
import shutil
import time

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'saves')
SLOTS = 3
VERSION = 1
PARTY_MAX = 6   # 필드에 놓는 자리 수: 0~2 앞줄(위·가운데·아래), 3~5 뒷줄
START_INK = 600  # 처음 검정 잉크 양 (PRD 2.6: 처음엔 검정뿐). 유닛 하나에 보통 150~280 → 처음에 둘쯤 놓을 수 있게

current = None        # 지금 하고 있는 세이브 (dict)
_session_start = None  # 플레이 시간을 재기 시작한 시각


def _path(slot, folder=None):
    return os.path.join(folder or DIR, f'slot_{slot}.json')


def _check(slot):
    if not 1 <= slot <= SLOTS:
        raise ValueError(f'slot must be 1..{SLOTS}: {slot}')


def blank(slot, now=None):
    """새 게임의 세이브 내용."""
    now = time.time() if now is None else now
    return {
        'version': VERSION,
        'slot': slot,
        'created_at': now,
        'saved_at': now,
        'play_time': 0.0,     # 초
        'stage': 0,           # 여정 진행 (0 = 아직 첫 필드 전)
        'intro_seen': False,  # 도입 이야기(컷씬)를 봤는가 — 보기 전이면 준비 화면 전에 보여 준다
        'ink': {'black': START_INK, 'red': 0, 'green': 0, 'blue': 0},
        'units': [],          # 그린 유닛 (프리셋): {'id', 'frame', 'body', 'counts', 'ink'} — 그림은 unit_path·gear_path
        'party': [None] * PARTY_MAX,  # 내 유닛: 필드 자리마다 놓은 프리셋 id (빈 자리 None, 같은 id 여러 번 가능)
        'party_hp': [1.0] * PARTY_MAX,  # 자리마다 남은 체력 비율 (1 가득 ~ 0 쓰러짐). 전투가 끝나도 이어지고 치료해야 찬다
        'cleared': [],        # 깬 스테이지 ('0-1' …)
    }


def exists(slot, folder=None):
    return os.path.exists(_path(slot, folder))


def load(slot, folder=None):
    """세이브를 읽는다. 없거나 깨졌으면 None. 빠진 항목은 새 게임 값으로 채운다."""
    _check(slot)
    try:
        with open(_path(slot, folder), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    full = blank(slot, data.get('created_at'))
    full.update({k: v for k, v in data.items() if k in full})
    full['slot'] = slot
    full['party'] = normalize_party(full['party'], full['units'])
    hp = full.get('party_hp') if isinstance(full.get('party_hp'), list) else []
    full['party_hp'] = [min(1.0, max(0.0, float(h))) if isinstance(h, (int, float)) else 1.0
                        for h in (hp + [1.0] * PARTY_MAX)[:PARTY_MAX]]
    return full


def write(data, folder=None):
    """data 를 그 슬롯 파일에 쓴다. 쓰는 도중 꺼져도 예전 파일이 깨지지 않게 임시 파일에 쓴 뒤 바꾼다."""
    slot = data['slot']
    _check(slot)
    folder = folder or DIR
    os.makedirs(folder, exist_ok=True)
    tmp = _path(slot, folder) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _path(slot, folder))


def delete(slot, folder=None):
    _check(slot)
    try:
        os.remove(_path(slot, folder))
    except FileNotFoundError:
        pass
    shutil.rmtree(units_dir(slot, folder), ignore_errors=True)
    global current
    if current and current['slot'] == slot:
        current = None


def summary(slot, folder=None):
    """선택 화면용 요약: {'slot', 'stage', 'play_time', 'saved_at', 'ink_total'} 또는 None (빈 슬롯)."""
    data = load(slot, folder)
    if data is None:
        return None
    return {'slot': slot, 'stage': data['stage'], 'play_time': data['play_time'], 'saved_at': data['saved_at'],
            'ink_total': sum(data['ink'].values())}


# ---------------------------------------------------------------- 그린 유닛 (프리셋)
def units_dir(slot, folder=None):
    return os.path.join(folder or DIR, f'slot_{slot}_units')


def unit_path(slot, unit_id, folder=None):
    return os.path.join(units_dir(slot, folder), f'unit_{unit_id}.png')


def gear_path(slot, unit_id, folder=None, group=0):
    """무기 종이 그림 (무기 묶음마다 한 장: 원딜은 0 활, 1 화살)."""
    return os.path.join(units_dir(slot, folder), f'unit_{unit_id}_gear{group}.png')


def add_unit(data, frame, counts, ink_used, folder=None, body='medium'):
    """유닛 기록을 더한다. 가진 잉크는 줄지 않고, 이 유닛을 꺼낼 때 드는 잉크(ink_used)만 적어 둔다.
    그림 PNG 는 부른 쪽이 unit_path(사람 종이)·gear_path(무기 종이마다) 에 저장한다 (폴더는 여기서 만들어 둔다)."""
    unit_id = max((u['id'] for u in data['units']), default=0) + 1
    unit = {'id': unit_id, 'frame': frame, 'body': body, 'counts': dict(counts), 'ink': dict(ink_used)}
    data['units'].append(unit)
    os.makedirs(units_dir(data['slot'], folder), exist_ok=True)
    return unit


def delete_unit(data, unit_id, folder=None):
    """프리셋을 지운다. 내 유닛에 고른 것도 빠지고 그림 파일도 지운다. 없으면 False."""
    if not find_unit(data, unit_id):
        return False
    data['units'] = [u for u in data['units'] if u['id'] != unit_id]
    for slot, i in enumerate(data['party']):
        if i == unit_id:
            remove_from_party(data, slot)
    paths = [unit_path(data['slot'], unit_id, folder)] + glob.glob(
        os.path.join(units_dir(data['slot'], folder), f'unit_{unit_id}_gear*.png'))
    for path in paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    return True


def find_unit(data, unit_id):
    for u in data['units']:
        if u['id'] == unit_id:
            return u
    return None


def normalize_party(party, units=None):
    """party 를 자리 PARTY_MAX 개짜리 목록으로 (빈 자리는 None). 예전 세이브의 id 목록도 앞자리부터 채운다.
    units 를 주면 없어진 프리셋 자리는 비운다."""
    ids = list(party) if isinstance(party, list) else []
    ids = (ids + [None] * PARTY_MAX)[:PARTY_MAX]
    if units is not None:
        alive = {u['id'] for u in units}
        ids = [i if i in alive else None for i in ids]
    return ids


def party_units(data):
    """자리에 놓인 유닛 기록 목록 (빈 자리는 건너뛴다)."""
    return [u for u in (find_unit(data, i) for i in data['party'] if i is not None) if u]


def party_cost(data):
    """놓인 유닛들에 드는 잉크 합 (색별)."""
    total = {c: 0 for c in data['ink']}
    for u in party_units(data):
        for c, n in u.get('ink', {}).items():
            total[c] = total.get(c, 0) + n
    return total


def ink_left(data):
    """남은 잉크 = 가진 잉크 - 내 유닛에 놓은 유닛들에 드는 잉크 (놓으면 줄고 빼면 돌아온다)."""
    cost = party_cost(data)
    return {c: n - cost.get(c, 0) for c, n in data['ink'].items()}


def can_place(data, unit, slot=None):
    """unit 을 slot 에 놓아도 가진 잉크 안인가 (slot 에 있던 유닛은 빠진다고 친다).
    slot 이 None 이면 빈 자리가 있어야 한다."""
    if slot is None:
        if None not in data['party']:
            return False
        old = None
    else:
        old = find_unit(data, data['party'][slot]) if data['party'][slot] is not None else None
    cost = party_cost(data)
    for c, n in (old or {}).get('ink', {}).items():
        cost[c] = cost.get(c, 0) - n
    return all(cost.get(c, 0) + n <= data['ink'].get(c, 0) for c, n in unit.get('ink', {}).items())


def can_add(data, unit):
    return can_place(data, unit)


def place(data, slot, unit_id):
    """slot 자리에 프리셋을 놓는다 (있던 유닛은 바뀐다). 잉크가 모자라면 False."""
    unit = find_unit(data, unit_id)
    if not unit or not 0 <= slot < PARTY_MAX or not can_place(data, unit, slot):
        return False
    data['party'][slot] = unit_id
    hp_list(data)[slot] = 1.0   # 새로 놓은 유닛은 가득
    return True


def add_to_party(data, unit_id):
    """앞자리부터 첫 빈 자리에 놓는다. 놓은 자리 번호, 못 놓으면 None."""
    unit = find_unit(data, unit_id)
    if not unit or not can_place(data, unit):
        return None
    slot = data['party'].index(None)
    data['party'][slot] = unit_id
    hp_list(data)[slot] = 1.0
    return slot


def remove_from_party(data, slot):
    """자리에서 뺀다 (잉크는 돌아오고, 다친 상태는 사라진다)."""
    if 0 <= slot < PARTY_MAX:
        data['party'][slot] = None
        hp_list(data)[slot] = 1.0


def swap_slots(data, a, b):
    """두 자리를 맞바꾼다 (한쪽이 비었으면 옮기기). 남은 체력도 함께 옮겨 간다."""
    p, h = data['party'], hp_list(data)
    p[a], p[b] = p[b], p[a]
    h[a], h[b] = h[b], h[a]


def hp_list(data):
    """자리마다 남은 체력 비율 목록 (예전 세이브면 만들어 둔다)."""
    if not isinstance(data.get('party_hp'), list) or len(data['party_hp']) != PARTY_MAX:
        data['party_hp'] = [1.0] * PARTY_MAX
    return data['party_hp']


def hurt_slots(data):
    """다친(체력이 가득이 아닌) 유닛이 놓인 자리들."""
    return [s for s, uid in enumerate(data['party']) if uid is not None and hp_list(data)[s] < 1.0]


def heal_cost(data, slots, rate=1.0):
    """slots 유닛을 가득 치료하는 데 드는 잉크 {색: 양}: 흐려진 만큼 다시 칠한다고 쳐서
    색마다 (그 유닛을 그린 그 색 잉크 x 잃은 체력 비율) 의 합을 올림 (원소 색으로 칠한 유닛은 그 색도 든다).
    다친 유닛이 있으면 모두 합쳐 적어도 1."""
    total = {}
    for s in slots:
        unit = find_unit(data, data['party'][s])
        lost = 1 - hp_list(data)[s]
        if not unit or lost <= 0:
            continue
        for c, n in unit.get('ink', {}).items():
            total[c] = total.get(c, 0.0) + n * lost * rate
    cost = {c: math.ceil(v - 1e-9) for c, v in total.items() if v > 1e-9}
    if not cost and any(hp_list(data)[s] < 1 for s in slots if data['party'][s] is not None):
        cost = {'black': 1}
    return cost


def heal(data, slots, cost):
    """slots 자리 유닛을 가득 치료하고 잉크 cost {색: 양} 을 쓴다 (가진 잉크에서 정말로 빠진다). 모자라면 False."""
    left = ink_left(data)
    if any(left.get(c, 0) < n for c, n in cost.items()):
        return False
    for c, n in cost.items():
        data['ink'][c] = data['ink'].get(c, 0) - n
    for s in slots:
        hp_list(data)[s] = 1.0
    return True


# ---------------------------------------------------------------- 지금 하고 있는 세이브
def start(data, now=None):
    """data 를 지금 세이브로 고르고 플레이 시간 재기를 시작한다."""
    global current, _session_start
    current = data
    _session_start = time.time() if now is None else now
    return current


def new_game(slot, folder=None, now=None):
    data = blank(slot, now)
    write(data, folder)
    return start(data, now)


def continue_game(slot, folder=None, now=None):
    data = load(slot, folder)
    if data is None:
        raise FileNotFoundError(_path(slot, folder))
    return start(data, now)


def save_current(folder=None, now=None):
    """지금 세이브에 지난 저장 뒤 흐른 플레이 시간을 더해 저장한다. 고른 세이브가 없으면 아무것도 안 한다."""
    global _session_start
    if current is None:
        return False
    now = time.time() if now is None else now
    if _session_start is not None:
        current['play_time'] += max(0.0, now - _session_start)
    _session_start = now
    current['saved_at'] = now
    write(current, folder)
    return True


# ---------------------------------------------------------------- 보여 주기용 글자
def format_play_time(seconds):
    minutes = int(seconds // 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours}시간 {minutes}분' if hours else f'{minutes}분'


def format_saved_at(t):
    return time.strftime('%Y.%m.%d %H:%M', time.localtime(t))


def stage_name(stage):
    return '여정을 떠나기 전' if stage == 0 else f'여정 {stage}단계'
