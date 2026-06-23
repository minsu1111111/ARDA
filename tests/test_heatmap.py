"""
H3 빈닝 + output_schema 단위 테스트.
의존성: h3==3.7.7
"""

import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
from shared.h3_utils import particles_to_h3_heatmap, filter_waypoints, validate_h3_coverage
from shared.output_schema import build_output_json, OUTPUT_SCHEMA_VERSION
from config import TANK_ORIGIN_LAT, TANK_ORIGIN_LON, TANK_LENGTH_M, TANK_WIDTH_M


def _random_particles(n: int = 200, seed: int = 42):
    """수조 내부에 균등 분포 파티클 생성."""
    rng = np.random.default_rng(seed)
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(TANK_ORIGIN_LAT)))
    lats = TANK_ORIGIN_LAT + rng.uniform(0, TANK_WIDTH_M  * lat_per_m, n)
    lons = TANK_ORIGIN_LON + rng.uniform(0, TANK_LENGTH_M * lon_per_m, n)
    return lats, lons


def test_probabilities_sum_to_one():
    """H3 셀 확률의 합이 1.0인지 확인."""
    lats, lons = _random_particles(200)
    heatmap = particles_to_h3_heatmap(lats, lons, resolution=15)
    total = sum(v['probability'] for v in heatmap.values())
    assert abs(total - 1.0) < 1e-5, f"[실패] 확률 합 = {total:.8f} (기대: 1.0)"
    print(f"[통과] 확률 합계 검증: {total:.8f}")


def test_h3_coverage_nonzero():
    """H3 셀이 1개 이상 생성되는지 확인."""
    lats, lons = _random_particles(100)
    heatmap = particles_to_h3_heatmap(lats, lons, resolution=15)
    assert validate_h3_coverage(heatmap, min_cells=1), "[실패] H3 커버리지 0"
    print(f"[통과] H3 커버리지 검증: 셀 {len(heatmap)}개")


def test_filter_waypoints_threshold():
    """필터 후 모든 waypoint가 임계값 이상인지 확인."""
    lats, lons = _random_particles(500)
    heatmap = particles_to_h3_heatmap(lats, lons, resolution=15)
    threshold = 0.005
    waypoints = filter_waypoints(heatmap, threshold=threshold)

    for wp in waypoints:
        assert wp['probability'] >= threshold, (
            f"[실패] 임계값 미만 waypoint 포함: {wp['probability']}"
        )
    probs = [wp['probability'] for wp in waypoints]
    assert probs == sorted(probs, reverse=True), "[실패] waypoint 정렬 오류"
    print(f"[통과] 임계값 필터 검증: waypoint {len(waypoints)}개")


def test_output_schema_structure():
    """JSON 출력 스키마 필드 구조 확인."""
    lats, lons = _random_particles(100)
    heatmap = particles_to_h3_heatmap(lats, lons, resolution=15)
    waypoints = filter_waypoints(heatmap)

    output = build_output_json(
        waypoints=waypoints,
        sim_params={'n_particles': 100, 'total_time_s': 300},
    )

    assert output['schema_version'] == OUTPUT_SCHEMA_VERSION, "스키마 버전 불일치"
    assert isinstance(output['waypoints'], list), "waypoints가 리스트가 아님"

    required_keys = {'rank', 'h3_index', 'probability', 'centroid_lat', 'centroid_lon', 'count'}
    for wp in output['waypoints']:
        missing = required_keys - wp.keys()
        assert not missing, f"[실패] 필드 누락: {missing}"

    print(f"[통과] JSON 스키마 구조 검증: waypoint {len(output['waypoints'])}개")


def test_empty_particles_raises():
    """빈 파티클 배열 전달 시 ValueError 발생 확인."""
    try:
        particles_to_h3_heatmap(np.array([]), np.array([]))
        assert False, "[실패] ValueError가 발생하지 않음"
    except ValueError:
        print("[통과] 빈 배열 예외 처리 검증")


if __name__ == '__main__':
    test_probabilities_sum_to_one()
    test_h3_coverage_nonzero()
    test_filter_waypoints_threshold()
    test_output_schema_structure()
    test_empty_particles_raises()
    print("\n=== H3 빈닝 단위 테스트 전체 통과 ===")
