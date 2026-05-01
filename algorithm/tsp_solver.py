import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# 1. 두 위도/경도 사이의 직선 거리를 계산하는 간단한 함수 (테스트용)
def calculate_distance(lat1, lon1, lat2, lon2):
    # 실제로는 Haversine 공식이나 카카오맵/구글맵 API를 써야 정확하지만, 
    # 우선은 단순 유클리디안 거리로 테스트합니다.
    return int(math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 100000)

def solve_tsp(locations):
    """
    locations: [{"id": "센터", "lat": 35.1, "lon": 126.9}, {"id": "배송지A", "lat": 35.2, "lon": 127.0}, ...]
    첫 번째 인덱스(0)를 출발지(물류센터)로 가정합니다.
    """
    
    # 2. OR-Tools에 넣을 거리 행렬(Distance Matrix) 만들기
    # 모든 장소 간의 거리를 미리 표로 만들어 두는 작업입니다.
    num_locations = len(locations)
    distance_matrix = []
    for i in range(num_locations):
        row = []
        for j in range(num_locations):
            dist = calculate_distance(locations[i]["lat"], locations[i]["lon"], 
                                      locations[j]["lat"], locations[j]["lon"])
            row.append(dist)
        distance_matrix.append(row)

    # 3. OR-Tools 라우팅 모델 설정 (기본 세팅값들입니다)
    manager = pywrapcp.RoutingIndexManager(num_locations, 1, 0) # (장소 수, 차량 1대, 출발지 인덱스 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        # OR-Tools가 거리 행렬에서 값을 꺼내갈 수 있게 연결
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 4. 해찾기 실행
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    
    solution = routing.SolveWithParameters(search_parameters)

    # 5. 결과 해석 및 LIFO (역순) 배열 만들기
    if solution:
        index = routing.Start(0)
        route_order = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_order.append(locations[node_index]["id"])
            index = solution.Value(routing.NextVar(index))
        
        # route_order는 [센터, 배송지B, 배송지A, 배송지C] 순서로 나옵니다.
        # 물류센터(0번)를 제외하고 배송지 순서만 자른 뒤, 역순(LIFO)으로 뒤집습니다!
        delivery_only_route = route_order[1:] 
        lifo_order = list(reversed(delivery_only_route)) 
        
        return {
            "optimal_route": delivery_only_route, # 운전 기사님이 갈 순서
            "lifo_packing_order": lifo_order      # 짐을 실어야 할 역순 (빈 패킹 알고리즘에 들어갈 순서)
        }
    else:
        return {"error": "경로를 찾을 수 없습니다."}

# --- 테스트 실행 ---
if __name__ == "__main__":
    dummy_locations = [
        {"id": "물류센터", "lat": 35.1764, "lon": 126.9071}, # 전남대
        {"id": "목적지A", "lat": 35.1595, "lon": 126.8526}, # 광주시청 방향
        {"id": "목적지B", "lat": 35.1461, "lon": 126.9231}, # 조선대 방향
        {"id": "목적지C", "lat": 35.2045, "lon": 126.8673}  # 첨단 방향
    ]
    
    result = solve_tsp(dummy_locations)
    print("TSP 최적 경로:", result["optimal_route"])
    print("트럭 적재 순서 (LIFO):", result["lifo_packing_order"])