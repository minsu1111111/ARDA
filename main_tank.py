"""
수조 파이프라인 진입점.
python main_tank.py 로 실행.
결과: results/heatmap_*.png + results/waypoints_*.json
"""

import os
import sys

# 프로젝트 루트가 sys.path에 없을 경우를 대비
sys.path.insert(0, os.path.dirname(__file__))

from tank.heatmap_pipeline import run_tank_simulation

if __name__ == '__main__':
    print("=== ARDA 수조 파이프라인 시작 ===")
    print("설정: 수조 1m×0.5m, 파티클 500개, 300초 시뮬레이션\n")

    output = run_tank_simulation(
        u_pump=0.05,       # 5cm/s 펌프 기본값
        v_pump=0.01,
        save_path='results/',
    )

    print(f"\n=== 최종 Waypoint 상위 {min(3, len(output['waypoints']))}개 ===")
    for wp in output['waypoints'][:3]:
        print(f"  Rank {wp['rank']:2d}: H3={wp['h3_index'][-8:]}, "
              f"확률={wp['probability']*100:.2f}%, "
              f"위치=({wp['centroid_lat']:.7f}, {wp['centroid_lon']:.7f})")

    print("\n=== 파이프라인 완료 ===")
