"""
Greedy 3D Bin Packing — Extreme Points Method

트럭 좌표계:
  x = 너비  (0 ~ truck_width)
  y = 높이  (0 ~ truck_height)
  z = 깊이  (0 = 트럭 안쪽, truck_length = 문 쪽)

적재 순서(LIFO):
  리스트의 앞 상자일수록 트럭 안쪽(z 작은 방향)에 먼저 배치됩니다.
  마지막 배송지 상자가 문 쪽에 위치하게 됩니다.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass
class PlacedBox:
    box_id: str
    destination: str
    x: int  # 너비 방향 시작점
    y: int  # 높이 방향 시작점
    z: int  # 깊이 방향 시작점 (0 = 안쪽)
    width: int
    height: int
    length: int  # 깊이 방향 크기


# ── 핵심 유틸 함수 ──────────────────────────────────────────────────────────

def _overlaps(b: PlacedBox, x: int, y: int, z: int, w: int, h: int, l: int) -> bool:
    """두 직육면체가 겹치는지 확인합니다."""
    return not (
        x + w <= b.x or b.x + b.width  <= x or
        y + h <= b.y or b.y + b.height <= y or
        z + l <= b.z or b.z + b.length <= z
    )


def _is_inside_box(point: Tuple[int, int, int], b: PlacedBox) -> bool:
    """extreme point가 이미 놓인 상자 내부에 있는지 확인합니다."""
    px, py, pz = point
    return (b.x <= px < b.x + b.width and
            b.y <= py < b.y + b.height and
            b.z <= pz < b.z + b.length)


def _is_valid_ep(point: Tuple[int, int, int], placed: List[PlacedBox],
                 tw: int, th: int, tl: int) -> bool:
    """
    extreme point가 유효한지 확인합니다.
    - 트럭 범위 안에 있어야 함
    - 기존 상자 내부에 있으면 안 됨
    """
    px, py, pz = point
    if px >= tw or py >= th or pz >= tl:
        return False
    return not any(_is_inside_box(point, b) for b in placed)


# ── 메인 함수 ────────────────────────────────────────────────────────────────

def greedy_pack(
    truck_width: int,
    truck_height: int,
    truck_length: int,
    boxes_in_lifo_order: List[Dict]
) -> Dict:
    """
    Greedy Extreme Points 방식으로 3D 빈 패킹을 수행합니다.

    Parameters
    ----------
    truck_width   : 트럭 너비
    truck_height  : 트럭 높이
    truck_length  : 트럭 깊이(앞뒤 길이)
    boxes_in_lifo_order : TSP solve_tsp()의 lifo_packing_order 순서로 정렬된 상자 목록.
        각 항목은 {"box_id", "width", "height", "length", "destination"} 형식.

    Returns
    -------
    {
        "packed": [ { "box_id", "destination", "position": {x,y,z}, "size": {w,h,l} }, ... ],
        "unpacked": ["box_id", ...],   # 공간 부족으로 못 실은 상자
        "utilization_pct": float       # 트럭 부피 활용률(%)
    }
    """
    placed: List[PlacedBox] = []
    unpacked: List[str] = []

    # 처음 배치 가능 지점은 트럭 안쪽 바닥 왼쪽 모서리
    extreme_points: List[Tuple[int, int, int]] = [(0, 0, 0)]

    for box_data in boxes_in_lifo_order:
        box_id  = box_data["box_id"]
        w       = box_data["width"]
        h       = box_data["height"]
        l       = box_data["length"]
        dest    = box_data.get("destination", "")

        best_pos: Optional[Tuple[int, int, int]] = None

        # extreme point를 (z 오름차순, y 오름차순, x 오름차순)으로 탐색
        # → 안쪽 아래 왼쪽을 우선적으로 채움
        for ep in sorted(extreme_points, key=lambda p: (p[2], p[1], p[0])):
            px, py, pz = ep

            # 트럭 범위 초과 여부 확인
            if px + w > truck_width:
                continue
            if py + h > truck_height:
                continue
            if pz + l > truck_length:
                continue

            # 기존 배치 상자와 겹침 여부 확인
            if any(_overlaps(b, px, py, pz, w, h, l) for b in placed):
                continue

            best_pos = (px, py, pz)
            break  # 가장 우선순위 높은 위치 찾으면 즉시 배치

        if best_pos is None:
            unpacked.append(box_id)
            continue

        px, py, pz = best_pos
        placed_box = PlacedBox(
            box_id=box_id,
            destination=dest,
            x=px, y=py, z=pz,
            width=w, height=h, length=l
        )
        placed.append(placed_box)

        # 새 상자의 세 면에서 extreme point 추가
        # - 오른쪽 면 (x 방향)
        extreme_points.append((px + w, py, pz))
        # - 윗면 (y 방향)
        extreme_points.append((px, py + h, pz))
        # - 앞면 (z 방향, 문 쪽)
        extreme_points.append((px, py, pz + l))

        # 무효 extreme point 제거 (트럭 외부 또는 상자 내부)
        extreme_points = [
            ep for ep in extreme_points
            if _is_valid_ep(ep, placed, truck_width, truck_height, truck_length)
        ]

    # 적재율 계산
    truck_volume = truck_width * truck_height * truck_length
    packed_volume = sum(b.width * b.height * b.length for b in placed)
    utilization = round(packed_volume / truck_volume * 100, 2) if truck_volume > 0 else 0.0

    return {
        "packed": [
            {
                "box_id": b.box_id,
                "destination": b.destination,
                "position": {"x": b.x, "y": b.y, "z": b.z},
                "size": {"width": b.width, "height": b.height, "length": b.length}
            }
            for b in placed
        ],
        "unpacked": unpacked,
        "utilization_pct": utilization
    }


# ── 단독 실행 테스트 ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    truck = {"width": 240, "height": 200, "length": 400}  # 단위: cm

    # TSP LIFO 결과를 시뮬레이션 (마지막 배송지 상자가 리스트 앞에)
    test_boxes = [
        {"box_id": "box_C1", "width": 60, "height": 60, "length": 60, "destination": "목적지C"},
        {"box_id": "box_C2", "width": 40, "height": 40, "length": 40, "destination": "목적지C"},
        {"box_id": "box_B1", "width": 80, "height": 60, "length": 80, "destination": "목적지B"},
        {"box_id": "box_A1", "width": 50, "height": 50, "length": 50, "destination": "목적지A"},
        {"box_id": "box_A2", "width": 30, "height": 70, "length": 30, "destination": "목적지A"},
    ]

    result = greedy_pack(
        truck_width=truck["width"],
        truck_height=truck["height"],
        truck_length=truck["length"],
        boxes_in_lifo_order=test_boxes
    )

    print(f"\n[Greedy 3D 빈 패킹 결과]")
    print(f"적재 성공: {len(result['packed'])}개 | 실패: {len(result['unpacked'])}개")
    print(f"트럭 부피 활용률: {result['utilization_pct']}%\n")
    for item in result["packed"]:
        p = item["position"]
        s = item["size"]
        print(f"  {item['box_id']} ({item['destination']}) "
              f"→ 위치 ({p['x']}, {p['y']}, {p['z']}) "
              f"크기 {s['width']}×{s['height']}×{s['length']}")
    if result["unpacked"]:
        print(f"\n  미적재 상자: {result['unpacked']}")
