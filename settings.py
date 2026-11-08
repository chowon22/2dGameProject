"""게임 설정 값. data/settings.json 에 저장하고 불러온다 (PRD 9.2 #11: 데이터는 JSON으로 분리).

pico2d 와 무관한 순수 로직이라 따로 테스트할 수 있다.
"""
import json
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'settings.json')

DEFAULTS = {
    'bgm_volume': 0.7,   # 배경음 0~1 (사운드가 들어가면 사용)
    'sfx_volume': 0.8,   # 효과음 0~1
    'brush_trail': True,  # 마우스 붓자국 효과
    'light_motes': True,  # 떠다니는 빛 입자·비눗방울 효과
    'title_theme': 'doodle',  # 타이틀 그림체: 'doodle'(낙서체) / 'dreamy'(몽환) / 'sketchbook'(스케치북) / 'ink'(잉크로 물드는 동화) / 'pastel'(처음 만든 파스텔 수채화)
}

THEMES = ('doodle', 'dreamy', 'sketchbook', 'ink', 'pastel')

_values = dict(DEFAULTS)


def load(path=None):
    path = path or PATH
    _values.clear()
    _values.update(DEFAULTS)
    try:
        with open(path, encoding='utf-8') as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return
    for key, default in DEFAULTS.items():
        if key in saved and type(saved[key]) is type(default):
            _values[key] = saved[key]
    for key in ('bgm_volume', 'sfx_volume'):
        _values[key] = min(1.0, max(0.0, float(_values[key])))
    if _values['title_theme'] not in THEMES:
        _values['title_theme'] = DEFAULTS['title_theme']


def save(path=None):
    path = path or PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(_values, f, ensure_ascii=False, indent=2)


def get(key):
    return _values[key]


def set(key, value):
    if key not in DEFAULTS:
        raise KeyError(key)
    if isinstance(DEFAULTS[key], float):
        value = min(1.0, max(0.0, float(value)))
    _values[key] = value
