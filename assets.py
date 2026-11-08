"""image 폴더의 이미지를 경로로 불러오고, 같은 파일은 한 번만 읽는다."""
import os

from pico2d import load_image

import settings

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(ROOT, 'image')

_cache = {}

# 그림체(테마)마다 이미지 폴더가 다르다. 파일 이름은 같다.
THEME_FOLDERS = {
    'doodle': {'title': 'title_doodle', 'settings': 'settings_doodle'},
    'dreamy': {'title': 'title', 'settings': 'settings'},
    'sketchbook': {'title': 'title_sketch', 'settings': 'settings_sketch'},
    'ink': {'title': 'title_ink', 'settings': 'settings_ink'},
    'pastel': {'title': 'title_pastel', 'settings': 'settings_pastel'},
    'restore': {'title': 'title_restore', 'settings': 'settings_pastel'},
}


# 폴더에 없는 파일은 바탕이 되는 그림체 폴더에서 찾는다 (같은 그림을 복사해 두지 않으려고)
FALLBACK = {'title_restore': 'title_pastel'}


def _resolve(parts):
    path = os.path.join(IMAGE_DIR, *parts)
    if not os.path.exists(path) and parts and parts[0] in FALLBACK:
        return _resolve((FALLBACK[parts[0]],) + tuple(parts[1:]))
    return path


def exists(*parts):
    return os.path.exists(_resolve(parts))


def folder(name):
    """folder('title') → 지금 고른 그림체의 타이틀 이미지 폴더."""
    return THEME_FOLDERS[settings.get('title_theme')].get(name, name)


def image(*parts):
    """image('title', 'logo.png') → image/title/logo.png. open_canvas() 뒤에만 부를 수 있다."""
    path = _resolve(parts)
    if path not in _cache:
        _cache[path] = load_image(path)
    return _cache[path]
