"""세이브 파일. 슬롯마다 data/saves/slot_<n>.json 하나 (PRD 9.2 #11: 데이터는 JSON으로 분리).

pico2d 와 무관한 순수 로직이라 따로 테스트할 수 있다 (tests/test_save_data.py).

- new_game(slot): 새 세이브를 만들어 저장하고 지금 슬롯으로 고른다
- load(slot) / summary(slot): 불러오기 / 선택 화면에 보일 요약 (없으면 None)
- save_current(): 지금 슬롯을 저장 (플레이 시간을 더한다)
- delete(slot): 지우기
"""
import json
import os
import time

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'saves')
SLOTS = 3
VERSION = 1
START_INK = 300  # 처음 검정 잉크 양 (PRD 2.6: 처음엔 검정뿐) — 수치는 미정 사항, 나중에 조정

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
        'ink': {'black': START_INK, 'red': 0, 'green': 0, 'blue': 0},
        'units': [],          # 그린 유닛 (PNG 경로·틀·색 비율 …) — 준비 화면이 생기면 채운다
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
