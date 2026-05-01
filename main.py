from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

# 방금 만든 tsp_solver 파일에서 solve_tsp 함수를 불러옵니다!
from tsp_solver import solve_tsp 

app = FastAPI(title="3D 빈 패킹 API")

# (이전과 동일한 데이터 모델)
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
    lat: float  # TSP 계산을 위해 위도/경도를 추가로 받도록 수정
    lon: float

class PackingRequest(BaseModel):
    truck_size: TruckSize
    boxes: List[BoxData]

@app.post("/api/v1/optimize-packing")
async def calculate_packing(request: PackingRequest):
    """
    들어온 상자 데이터를 바탕으로 TSP 최적 경로를 계산하고 반환합니다.
    """
    
    # 1. 클라이언트(Unity/웹)가 보낸 데이터에서 TSP 함수에 넣을 형식으로 리스트를 만듭니다.
    # 물류센터(출발지) 좌표는 고정값으로 하나 넣어줍니다.
    locations_for_tsp = [{"id": "물류센터", "lat": 35.1764, "lon": 126.9071}] 
    
    # 클라이언트가 보낸 상자들의 목적지 좌표를 뒤에 붙입니다.
    for box in request.boxes:
        locations_for_tsp.append({
            "id": box.box_id,  # 상자 ID를 목적지 이름 대신 사용
            "lat": box.lat,
            "lon": box.lon
        })

    # 2. 방금 우리가 만든 TSP 함수 실행!
    tsp_result = solve_tsp(locations_for_tsp)

    # 에러 처리
    if "error" in tsp_result:
         return {"status": "fail", "message": tsp_result["error"]}

    # 3. 계산된 결과를 응답으로 돌려줍니다.
    return {
        "status": "success",
        "total_boxes_packed": len(request.boxes),
        "route_order": tsp_result["optimal_route"],
        "packing_order_lifo": tsp_result["lifo_packing_order"],
        "message": "TSP 계산이 완료되었습니다. (3D 빈 패킹 좌표 계산은 4주차에 구현 예정!)"
    }