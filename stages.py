"""월드·스테이지·몬스터 데이터 (data/stages.json, data/monsters.json — PRD 9.2 #11). pico2d 와 무관한 순수 로직.

- 월드 0 ~ 7, 월드마다 스테이지 'w-1' ~ 'w-7' (아직 데이터가 없는 월드는 '준비 중')
- 스테이지 열림: 월드의 첫 스테이지는 그 월드가 열리면, 다음 스테이지는 앞 스테이지를 깨면. 월드 w 는 월드 w-1 의 마지막 스테이지를 깨면
- enemies(sid): 스테이지 적들 (몬스터 능력치 x 스테이지 level, 자리 0~5 — 내 유닛 자리와 같은 배치)
- clear(data, sid): 깬 스테이지 적고 떨어뜨린 잉크를 더한다
"""
import json
import os

import stats

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
STAGES_PER_WORLD = 7
_data = {}


def _load(name):
    if name not in _data:
        with open(os.path.join(DIR, name + '.json'), encoding='utf-8') as f:
            _data[name] = json.load(f)
    return _data[name]


def worlds():
    return _load('stages')['worlds']


def stage_ids(world):
    return [f'{world}-{i}' for i in range(1, STAGES_PER_WORLD + 1)]


def stage(sid):
    """스테이지 데이터 (없으면 None — 아직 준비 중)."""
    return _load('stages')['stages'].get(sid)


def monster(mid):
    return _load('monsters')[mid]


def enemies(sid):
    """[{'mid', 'name', 'image', 'scale', 'slot', 'hp', 'atk', 'element', 'strength', 'drop', 'power'}]."""
    st = stage(sid)
    if not st:
        return []
    level = st.get('level', 1.0)
    out = []
    for mid, slot in st['enemies']:
        m = monster(mid)
        hp, atk = round(m['hp'] * level), round(m['atk'] * level, 1)
        out.append({'mid': mid, 'name': m['name'], 'image': tuple(m['image']), 'scale': m.get('scale', 1.0),
                    'slot': slot, 'hp': hp, 'atk': atk, 'buff': 0, 'element': m.get('element'), 'strength': 0.5,
                    'drop': dict(m.get('drop', {})), 'power': stats.power(hp, atk), 'role': 'monster'})
    return out


def cleared(data):
    return data.setdefault('cleared', [])


def is_cleared(data, sid):
    return sid in cleared(data)


def world_unlocked(data, world):
    return world == 0 or is_cleared(data, f'{world - 1}-{STAGES_PER_WORLD}')


def unlocked(data, sid):
    world, n = (int(x) for x in sid.split('-'))
    if not world_unlocked(data, world) or stage(sid) is None:
        return False
    return n == 1 or is_cleared(data, f'{world}-{n - 1}')


def drops(sid):
    """스테이지를 깨면 받는 잉크 (적들이 떨어뜨린 것 합)."""
    total = {}
    for e in enemies(sid):
        for c, n in e['drop'].items():
            total[c] = total.get(c, 0) + n
    return total


def clear(data, sid):
    """깬 스테이지를 적고 잉크를 더한다. 받은 잉크를 돌려준다."""
    got = drops(sid)
    for c, n in got.items():
        data['ink'][c] = data['ink'].get(c, 0) + n
    if sid not in cleared(data):
        cleared(data).append(sid)
    return got
