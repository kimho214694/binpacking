"""
3D 빈 패킹 시각화 — Plotly

트럭 내부 상자 배치를 브라우저에서 3D로 확인합니다.
마우스로 회전/줌 가능합니다.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import plotly.graph_objects as go
from algorithm.greedy_packer import greedy_pack

# ── 색상 팔레트 (목적지별 구분) ──────────────────────────────────────────────

COLORS = [
    "rgba(99, 149, 255, 0.75)",   # 파랑
    "rgba(255, 107, 107, 0.75)",  # 빨강
    "rgba(80, 200, 120, 0.75)",   # 초록
    "rgba(255, 183, 77, 0.75)",   # 주황
    "rgba(180, 100, 255, 0.75)",  # 보라
    "rgba(0, 210, 210, 0.75)",    # 청록
    "rgba(255, 150, 200, 0.75)",  # 분홍
]


# ── 박스 메시 생성 ────────────────────────────────────────────────────────────

def _box_vertices(x, y, z, w, h, l):
    """박스의 8개 꼭짓점 좌표를 반환합니다."""
    return (
        [x,   x+w, x+w, x,   x,   x+w, x+w, x  ],  # X
        [y,   y,   y+h, y+h, y,   y,   y+h, y+h],  # Y
        [z,   z,   z,   z,   z+l, z+l, z+l, z+l],  # Z
    )


def make_box_mesh(x, y, z, w, h, l, color, name):
    """Plotly Mesh3d로 색칠된 3D 박스를 생성합니다."""
    vx, vy, vz = _box_vertices(x, y, z, w, h, l)

    # 6면을 12개 삼각형으로 분할
    i = [0, 0,  4, 4,  0, 0,  2, 2,  0, 0,  1, 1]
    j = [1, 2,  5, 6,  1, 5,  3, 7,  3, 7,  2, 6]
    k = [2, 3,  6, 7,  5, 4,  7, 6,  7, 4,  6, 5]

    return go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=i, j=j, k=k,
        color=color,
        opacity=0.75,
        name=name,
        hovertemplate=(
            f"<b>{name}</b><br>"
            f"위치: ({x}, {y}, {z})<br>"
            f"크기: {w}×{h}×{l}<br>"
            f"목적지: {name.split('|')[1].strip() if '|' in name else ''}"
            "<extra></extra>"
        ),
        showlegend=True,
    )


def make_box_edges(x, y, z, w, h, l, color):
    """박스 테두리 선을 생성합니다 (윤곽선 강조용)."""
    # 12개 엣지를 None으로 분리해 한 번에 그림
    edges = [
        # 아랫면
        [(x, x+w), (y, y),   (z, z)],
        [(x+w, x+w), (y, y+h), (z, z)],
        [(x+w, x),   (y+h, y+h), (z, z)],
        [(x, x),     (y+h, y), (z, z)],
        # 윗면
        [(x, x+w), (y, y),   (z+l, z+l)],
        [(x+w, x+w), (y, y+h), (z+l, z+l)],
        [(x+w, x),   (y+h, y+h), (z+l, z+l)],
        [(x, x),     (y+h, y), (z+l, z+l)],
        # 기둥
        [(x, x),     (y, y),   (z, z+l)],
        [(x+w, x+w), (y, y),   (z, z+l)],
        [(x+w, x+w), (y+h, y+h), (z, z+l)],
        [(x, x),     (y+h, y+h), (z, z+l)],
    ]

    ex, ey, ez = [], [], []
    for (x1, x2), (y1, y2), (z1, z2) in edges:
        ex += [x1, x2, None]
        ey += [y1, y2, None]
        ez += [z1, z2, None]

    return go.Scatter3d(
        x=ex, y=ey, z=ez,
        mode="lines",
        line=dict(color="rgba(0,0,0,0.5)", width=2),
        showlegend=False,
        hoverinfo="skip",
    )


def make_truck_wireframe(tw, th, tl):
    """트럭 외곽 와이어프레임을 생성합니다."""
    x = [0, tw, tw, 0,  0,  0, tw, tw, 0,  0,  tw, tw]
    y = [0, 0,  th, th, 0,  0, 0,  th, th, 0,  0,  th]
    z = [0, 0,  0,  0,  0, tl, tl, tl, tl, tl, tl, tl]

    # 트럭 꼭짓점 8개 연결
    vx = [0, tw, tw, 0,  0,  None, 0,  0,  None, tw, tw, None, 0,  tw, None, 0, tw]
    vy = [0, 0,  th, th, 0,  None, 0,  0,  None, 0,  0,  None, th, th, None, 0, 0 ]
    vz = [0, 0,  0,  0,  0,  None, 0,  tl, None, 0,  tl, None, 0,  0,  None, tl, tl]

    # 12개 엣지
    edges = [
        # 아랫면
        ([0,tw],[0,0],[0,0]), ([tw,tw],[0,th],[0,0]),
        ([tw,0],[th,th],[0,0]), ([0,0],[th,0],[0,0]),
        # 윗면
        ([0,tw],[0,0],[tl,tl]), ([tw,tw],[0,th],[tl,tl]),
        ([tw,0],[th,th],[tl,tl]), ([0,0],[th,0],[tl,tl]),
        # 기둥
        ([0,0],[0,0],[0,tl]), ([tw,tw],[0,0],[0,tl]),
        ([tw,tw],[th,th],[0,tl]), ([0,0],[th,th],[0,tl]),
    ]

    ex, ey, ez = [], [], []
    for (x1,x2),(y1,y2),(z1,z2) in edges:
        ex += [x1, x2, None]
        ey += [y1, y2, None]
        ez += [z1, z2, None]

    return go.Scatter3d(
        x=ex, y=ey, z=ez,
        mode="lines",
        line=dict(color="rgba(50,50,50,0.9)", width=4),
        name="트럭",
        showlegend=True,
        hoverinfo="skip",
    )


# ── 메인 시각화 함수 ──────────────────────────────────────────────────────────

def visualize(truck_width, truck_height, truck_length, packing_result):
    """
    greedy_pack() 결과를 받아 3D 시각화를 브라우저로 출력합니다.

    Parameters
    ----------
    truck_width, truck_height, truck_length : 트럭 치수
    packing_result : greedy_pack()의 반환값
    """
    traces = []

    # 트럭 외곽선
    traces.append(make_truck_wireframe(truck_width, truck_height, truck_length))

    # 목적지별 색상 매핑
    destinations = list(dict.fromkeys(
        item["destination"] for item in packing_result["packed"]
    ))
    dest_color = {d: COLORS[i % len(COLORS)] for i, d in enumerate(destinations)}

    # 상자 렌더링
    for item in packing_result["packed"]:
        p = item["position"]
        s = item["size"]
        color = dest_color[item["destination"]]
        label = f"{item['box_id']} | {item['destination']}"

        traces.append(make_box_mesh(
            p["x"], p["y"], p["z"],
            s["width"], s["height"], s["length"],
            color, label
        ))
        traces.append(make_box_edges(
            p["x"], p["y"], p["z"],
            s["width"], s["height"], s["length"],
            color
        ))

    # 레이아웃
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(
            text=(
                f"3D 빈 패킹 결과 — "
                f"적재 {len(packing_result['packed'])}개 / "
                f"미적재 {len(packing_result['unpacked'])}개 / "
                f"활용률 {packing_result['utilization_pct']}%"
            ),
            font=dict(size=16)
        ),
        scene=dict(
            xaxis=dict(title="너비 (X)", range=[0, truck_width]),
            yaxis=dict(title="높이 (Y)", range=[0, truck_height]),
            zaxis=dict(title="깊이 (Z) ← 안쪽  문 쪽 →", range=[0, truck_length]),
            aspectmode="data",
            camera=dict(eye=dict(x=1.8, y=1.2, z=1.2)),
        ),
        legend=dict(x=0, y=1),
        margin=dict(l=0, r=0, t=60, b=0),
    )

    fig.show()
    print(f"\n[시각화 완료]")
    print(f"  적재 성공: {len(packing_result['packed'])}개")
    print(f"  미적재:   {len(packing_result['unpacked'])}개")
    print(f"  활용률:   {packing_result['utilization_pct']}%")


# ── 테스트 실행 ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    truck = {"width": 240, "height": 200, "length": 400}

    # TSP LIFO 결과 시뮬레이션 (마지막 배송지가 앞에)
    boxes_lifo = [
        {"box_id": "box_C1", "width": 60,  "height": 60,  "length": 60,  "destination": "목적지C"},
        {"box_id": "box_C2", "width": 40,  "height": 40,  "length": 40,  "destination": "목적지C"},
        {"box_id": "box_B1", "width": 80,  "height": 60,  "length": 80,  "destination": "목적지B"},
        {"box_id": "box_B2", "width": 50,  "height": 80,  "length": 50,  "destination": "목적지B"},
        {"box_id": "box_A1", "width": 100, "height": 80,  "length": 100, "destination": "목적지A"},
        {"box_id": "box_A2", "width": 60,  "height": 100, "length": 60,  "destination": "목적지A"},
        {"box_id": "box_A3", "width": 80,  "height": 60,  "length": 80,  "destination": "목적지A"},
    ]

    result = greedy_pack(
        truck_width=truck["width"],
        truck_height=truck["height"],
        truck_length=truck["length"],
        boxes_in_lifo_order=boxes_lifo
    )

    visualize(
        truck_width=truck["width"],
        truck_height=truck["height"],
        truck_length=truck["length"],
        packing_result=result
    )
