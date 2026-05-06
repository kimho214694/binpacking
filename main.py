import os
import tempfile
import shutil

from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel
from typing import List

from algorithm.tsp_solver import solve_tsp
from algorithm.greedy_packer import greedy_pack
from vision.box_detector import measure_box

app = FastAPI(title="3D 빈 패킹 API")


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

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


# ── 공통 로직 ─────────────────────────────────────────────────────────────────

def _run_tsp_and_pack(truck_size: TruckSize, boxes: List[BoxData]):
    """TSP 경로 최적화 → LIFO 정렬 → Greedy 3D 빈 패킹 수행."""

    # 1단계: TSP
    locations = [{"id": "물류센터", "lat": 35.1764, "lon": 126.9071}]
    for b in boxes:
        locations.append({"id": b.box_id, "lat": b.lat, "lon": b.lon})

    tsp_result = solve_tsp(locations)
    if "error" in tsp_result:
        return None, tsp_result["error"]

    lifo_order: List[str] = tsp_result["lifo_packing_order"]

    # 2단계: LIFO 순서로 정렬
    box_map = {b.box_id: b for b in boxes}
    boxes_for_packing = [
        {"box_id": b.box_id, "width": b.width, "height": b.height,
         "length": b.length, "destination": b.destination}
        for box_id in lifo_order
        if (b := box_map.get(box_id))
    ]

    # 3단계: Greedy 패킹
    packing_result = greedy_pack(
        truck_width=truck_size.width,
        truck_height=truck_size.height,
        truck_length=truck_size.length,
        boxes_in_lifo_order=boxes_for_packing,
    )

    return {
        "status": "success",
        "total_boxes": len(boxes),
        "packed_count": len(packing_result["packed"]),
        "unpacked_count": len(packing_result["unpacked"]),
        "truck_utilization_pct": packing_result["utilization_pct"],
        "route_order": tsp_result["optimal_route"],
        "packing_order_lifo": lifo_order,
        "packed_boxes": packing_result["packed"],
        "unpacked_boxes": packing_result["unpacked"],
    }, None


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@app.post("/api/v1/optimize-packing")
async def calculate_packing(request: PackingRequest):
    """
    치수를 직접 입력해 TSP + Greedy 3D 빈 패킹을 수행합니다.
    """
    result, error = _run_tsp_and_pack(request.truck_size, request.boxes)
    if error:
        return {"status": "fail", "message": error}
    return result


@app.post("/api/v1/measure-box")
async def measure_box_endpoint(
    top_image:  UploadFile = File(..., description="위에서 찍은 사진 (가로/세로 측정)"),
    side_image: UploadFile = File(..., description="옆에서 찍은 사진 (높이 측정)"),
):
    """
    두 장 사진을 업로드하면 상자의 W, L, H를 cm 단위로 반환합니다.

    촬영 조건:
    - A4 용지를 상자 옆에 기준물체로 놓고 촬영
    - 배경은 어두운 색 권장
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        top_path  = os.path.join(tmp_dir, top_image.filename)
        side_path = os.path.join(tmp_dir, side_image.filename)

        with open(top_path, "wb") as f:
            shutil.copyfileobj(top_image.file, f)
        with open(side_path, "wb") as f:
            shutil.copyfileobj(side_image.file, f)

        dimensions = measure_box(top_path, side_path)

        if dimensions is None:
            return {
                "status": "fail",
                "message": "치수 측정 실패. A4 용지와 상자가 모두 화면에 보이는지 확인하세요.",
            }

        return {
            "status": "success",
            "dimensions_cm": dimensions,
            "guide": "반환된 치수를 /api/v1/optimize-packing 요청의 width/length/height에 사용하세요.",
        }
    finally:
        shutil.rmtree(tmp_dir)


@app.post("/api/v1/measure-and-pack")
async def measure_and_pack(
    top_image:    UploadFile = File(...,   description="위에서 찍은 사진"),
    side_image:   UploadFile = File(...,   description="옆에서 찍은 사진"),
    box_id:       str        = Form(...,   description="상자 ID (예: box_001)"),
    destination:  str        = Form(...,   description="배송지 이름"),
    lat:          float      = Form(...,   description="배송지 위도"),
    lon:          float      = Form(...,   description="배송지 경도"),
    truck_width:  int        = Form(...,   description="트럭 너비 (cm)"),
    truck_height: int        = Form(...,   description="트럭 높이 (cm)"),
    truck_length: int        = Form(...,   description="트럭 길이 (cm)"),
):
    """
    사진 촬영 → 치수 자동 측정 → TSP + Greedy 패킹을 한 번에 수행합니다.

    단일 상자 기준. 여러 상자는 /api/v1/optimize-packing을 사용하세요.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        top_path  = os.path.join(tmp_dir, top_image.filename)
        side_path = os.path.join(tmp_dir, side_image.filename)

        with open(top_path, "wb") as f:
            shutil.copyfileobj(top_image.file, f)
        with open(side_path, "wb") as f:
            shutil.copyfileobj(side_image.file, f)

        dimensions = measure_box(top_path, side_path)
        if dimensions is None:
            return {"status": "fail", "message": "치수 측정 실패."}

        box = BoxData(
            box_id=box_id,
            width=int(dimensions["width"]),
            length=int(dimensions["length"]),
            height=int(dimensions["height"]),
            destination=destination,
            lat=lat,
            lon=lon,
        )
        truck = TruckSize(width=truck_width, height=truck_height, length=truck_length)

        result, error = _run_tsp_and_pack(truck, [box])
        if error:
            return {"status": "fail", "message": error}

        result["measured_dimensions_cm"] = dimensions
        return result

    finally:
        shutil.rmtree(tmp_dir)
