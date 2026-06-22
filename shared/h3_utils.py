"""
H3 빈닝 유틸리티.
h3==3.7.7 API 기준 (geo_to_h3 / h3_to_geo).
h3 4.x API(latlng_to_cell)와 혼용 금지.
"""

from collections import Counter
from typing import Dict, List

import h3
import numpy as np

from config import H3_RESOLUTION, WAYPOINT_THRESHOLD


def particles_to_h3_heatmap(
    lats: np.ndarray,
    lons: np.ndarray,
    resolution: int = H3_RESOLUTION,
) -> Dict[str, dict]:
    """
    파티클 위치 배열 → H3 셀별 확률 딕셔너리.

    Returns
    -------
    {
      '<h3_index>': {
        'probability': 0.134,
        'centroid_lat': 37.500012,
        'centroid_lon': 126.700034,
        'count': 67
      }, ...
    }
    """
    if len(lats) == 0:
        raise ValueError("파티클 배열이 비어있습니다. 시뮬레이션을 먼저 확인하세요.")

    cell_indices = [
        h3.geo_to_h3(float(lat), float(lon), resolution)
        for lat, lon in zip(lats, lons)
    ]

    counts = Counter(cell_indices)
    total = sum(counts.values())

    result = {}
    for cell_idx, count in counts.items():
        centroid_lat, centroid_lon = h3.h3_to_geo(cell_idx)
        result[cell_idx] = {
            'probability':   round(count / total, 6),
            'centroid_lat':  centroid_lat,
            'centroid_lon':  centroid_lon,
            'count':         count,
        }
    return result


def filter_waypoints(
    heatmap: Dict[str, dict],
    threshold: float = WAYPOINT_THRESHOLD,
) -> List[dict]:
    """
    확률 임계값(기본 0.5%) 이상 셀 필터링 → 내림차순 정렬 리스트.
    이다빈의 waypoint 생성 로직과 동일한 threshold 사용.
    """
    waypoints = [
        {'h3_index': k, **v}
        for k, v in heatmap.items()
        if v['probability'] >= threshold
    ]
    return sorted(waypoints, key=lambda x: x['probability'], reverse=True)


def validate_h3_coverage(heatmap: Dict[str, dict], min_cells: int = 1) -> bool:
    """H3 커버리지가 0%가 아닌지 확인하는 검증 체크포인트."""
    coverage = len(heatmap)
    print(f"[VALIDATE] H3 셀 수: {coverage} (최소 요구: {min_cells})")
    return coverage >= min_cells
