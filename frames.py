"""유닛 틀 4종 (PRD 4.1). pico2d 와 무관한 순수 데이터·로직.

틀마다 부위(머리·몸통·팔·다리 …)를 타원으로 적어 두고, 여기서
- silhouette(): 종이에 흐릿하게 깔리는 틀 실루엣 (RGBA)
- part_mask(): 픽셀마다 어느 부위인지 (나중에 그림을 부위 PNG 로 나눌 때 씀, PRD 9.1 #4)
를 만든다. 좌표는 종이 크기(PAPER_W x PAPER_H)의 왼쪽 위 (0, 0) 기준.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PAPER_W, PAPER_H = 760, 390
CX = PAPER_W // 2

# (부위 이름, 가운데 x, 가운데 y, 반지름 x, 반지름 y). 뒤에 적은 부위가 겹친 곳을 차지한다.
FRAMES = (
    {'id': 'tank', 'name': '탱커', 'stat': '체력', 'parts': (
        ('leg_l', CX - 52, 330, 34, 44), ('leg_r', CX + 52, 330, 34, 44),
        ('arm_l', CX - 128, 205, 42, 70), ('arm_r', CX + 128, 205, 42, 70),
        ('body', CX, 215, 110, 105), ('head', CX, 82, 60, 50))},
    {'id': 'melee', 'name': '근접 딜러', 'stat': '공격력', 'parts': (
        ('leg_l', CX - 34, 320, 22, 52), ('leg_r', CX + 34, 320, 22, 52),
        ('arm_l', CX - 112, 175, 62, 30), ('arm_r', CX + 120, 165, 76, 34),
        ('body', CX, 200, 64, 78), ('head', CX, 82, 48, 46))},
    {'id': 'ranged', 'name': '원거리 딜러', 'stat': '공격력', 'parts': (
        ('leg_l', CX - 26, 322, 18, 52), ('leg_r', CX + 26, 322, 18, 52),
        ('arm_l', CX - 78, 190, 22, 54), ('arm_r', CX + 150, 150, 110, 20),
        ('body', CX, 205, 52, 74), ('head', CX, 86, 54, 52))},
    {'id': 'support', 'name': '서포터', 'stat': '버프량', 'parts': (
        ('leg_l', CX - 30, 326, 22, 44), ('leg_r', CX + 30, 326, 22, 44),
        ('arm_l', CX - 92, 210, 30, 50), ('arm_r', CX + 92, 210, 30, 50),
        ('body', CX, 225, 72, 82), ('head', CX, 104, 52, 50), ('halo', CX, 34, 46, 14))},
)
IDS = tuple(f['id'] for f in FRAMES)


def get(frame_id):
    for f in FRAMES:
        if f['id'] == frame_id:
            return f
    raise KeyError(frame_id)


def part_names(frame_id):
    return [p[0] for p in get(frame_id)['parts']]


def part_mask(frame_id, size=(PAPER_W, PAPER_H)):
    """(h, w) uint8: 0 = 틀 밖, i = part_names()[i - 1]."""
    img = Image.new('L', size, 0)
    d = ImageDraw.Draw(img)
    sx, sy = size[0] / PAPER_W, size[1] / PAPER_H
    for i, (_, x, y, rx, ry) in enumerate(get(frame_id)['parts'], 1):
        d.ellipse(((x - rx) * sx, (y - ry) * sy, (x + rx) * sx, (y + ry) * sy), fill=i)
    return np.asarray(img)


def silhouette(frame_id, size=(PAPER_W, PAPER_H), color=(150, 128, 170), fill_alpha=46, line_alpha=110):
    """종이에 깔 흐릿한 틀 그림 (RGBA). 부위 안은 옅게 칠하고, 바깥 테두리만 조금 진하게."""
    inside = Image.fromarray(((part_mask(frame_id, size) > 0) * 255).astype(np.uint8), 'L')
    soft = inside.filter(ImageFilter.GaussianBlur(1.2))
    edge = np.asarray(soft.filter(ImageFilter.MaxFilter(5))).astype(np.int16) - np.asarray(soft.filter(
        ImageFilter.MinFilter(5))).astype(np.int16)
    a = np.maximum(np.asarray(soft).astype(np.float32) / 255 * fill_alpha,
                   np.clip(edge, 0, 255).astype(np.float32) / 255 * line_alpha)
    out = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    out[..., :3] = color
    out[..., 3] = a.astype(np.uint8)
    return out
