"""
강민수(수조) + 이다빈(한강)이 공유하는 JSON 출력 스키마.
드론 waypoint 소비 모듈이 이 형식을 읽는다.
스키마 구조 변경 시에만 OUTPUT_SCHEMA_VERSION을 올릴 것.
"""

from datetime import datetime
from typing import Dict, List

OUTPUT_SCHEMA_VERSION = '1.0.0'


def build_output_json(waypoints: List[Dict], sim_params: Dict) -> Dict:
    """
    표준 출력 JSON 생성.

    출력 형식
    ---------
    {
      "schema_version": "1.0.0",
      "generated_at": "2026-06-22T09:00:00",
      "sim_params": { "n_particles": 500, "total_time_s": 300, ... },
      "waypoints": [
        {
          "rank": 1,
          "h3_index": "8f2830828052d25",
          "probability": 0.134,
          "centroid_lat": 37.500012,
          "centroid_lon": 126.700034,
          "count": 67
        }, ...
      ]
    }

    h3_index   : h3-py 3.7.7 geo_to_h3() 반환값 (15자리 hex 문자열)
    probability: 0.0 ~ 1.0 (소수점 6자리)
    rank       : 1부터 시작, 확률 내림차순
    """
    ranked = []
    for i, wp in enumerate(waypoints, start=1):
        ranked.append({
            'rank':          i,
            'h3_index':      wp['h3_index'],
            'probability':   wp['probability'],
            'centroid_lat':  wp['centroid_lat'],
            'centroid_lon':  wp['centroid_lon'],
            'count':         wp['count'],
        })

    return {
        'schema_version': OUTPUT_SCHEMA_VERSION,
        'generated_at':   datetime.now().isoformat(),
        'sim_params':     sim_params,
        'waypoints':      ranked,
    }
