from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from algorithm.tsp_solver import solve_tsp
from algorithm.greedy_packer import greedy_pack

app = FastAPI(title="3D 빈 패킹 API")


class TruckSize(BaseModel):
    width: int
    length: int
    height: int


class BoxData(BaseModel):
    box_id: str
    width: int
    length: int
    height: int
    destination: str
    lat: float
    lon: float


class PackingRequest(BaseModel):
    truck_size: TruckSize
    boxes: List[BoxData]


@app.post("/api/v1/optimize-packing")
async def calculate_packing(request: PackingRequest):
    """
    1. TSP로 최적 배송 경로 계산
    2. LIFO 순서로 Greedy 3D 빈 패킹 수행
    3. 각 상자의 트럭 내 3D 좌표 반환
    """

    # ── 1단계: TSP 경로 최적화 ───────────────────────────────────────────────
    locations_for_tsp = [{"id": "물류센터", "lat": 35.1764, "lon": 126.9071}]
    for box in request.boxes:
        locations_for_tsp.append({
            "id": box.box_id,
            "lat": box.lat,
            "lon": box.lon
        })

    tsp_result = solve_tsp(locations_for_tsp)

    if "error" in tsp_result:
        return {"status": "fail", "message": tsp_result["error"]}

    lifo_order: List[str] = tsp_result["lifo_packing_order"]  # box_id 목록

    # ── 2단계: LIFO 순서로 상자 정렬 ────────────────────────────────────────
    box_map = {box.box_id: box for box in request.boxes}

    boxes_for_packing = []
    for box_id in lifo_order:
        if box_id in box_map:
            b = box_map[box_id]
            boxes_for_packing.append({
                "box_id": b.box_id,
                "width": b.width,
                "height": b.height,
                "length": b.length,
                "destination": b.destination
            })

    # ── 3단계: Greedy 3D 빈 패킹 ────────────────────────────────────────────
    packing_result = greedy_pack(
        truck_width=request.truck_size.width,
        truck_height=request.truck_size.height,
        truck_length=request.truck_size.length,
        boxes_in_lifo_order=boxes_for_packing
    )

    # ── 응답 ─────────────────────────────────────────────────────────────────
    return {
        "status": "success",
        "total_boxes": len(request.boxes),
        "packed_count": len(packing_result["packed"]),
        "unpacked_count": len(packing_result["unpacked"]),
        "truck_utilization_pct": packing_result["utilization_pct"],
        "route_order": tsp_result["optimal_route"],
        "packing_order_lifo": lifo_order,
        "packed_boxes": packing_result["packed"],
        "unpacked_boxes": packing_result["unpacked"]
    }
