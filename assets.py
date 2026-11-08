"""image 폴더의 이미지를 경로로 불러오고, 같은 파일은 한 번만 읽는다."""
import os

from pico2d import load_image

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(ROOT, 'image')

_cache = {}


def image(*parts):
    """image('title', 'logo.png') → image/title/logo.png. open_canvas() 뒤에만 부를 수 있다."""
    path = os.path.join(IMAGE_DIR, *parts)
    if path not in _cache:
        _cache[path] = load_image(path)
    return _cache[path]
