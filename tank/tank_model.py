"""
수조 전용 OpenDrift 서브클래스.

반사 경계(Reflective BC)로 파티클을 수조 안에 가둔다.
OpenDrift 1.14+에서는 deactivate_stranded()가 제거되었으므로,
대신 general:use_auto_landmask=False + environment:fallback:land_binary_mask=0 으로
GSHHG 해안선 판정을 비활성화한다.
"""

import math

import numpy as np
from opendrift.models.oceandrift import OceanDrift

from config import (
    TANK_ORIGIN_LAT, TANK_ORIGIN_LON,
    TANK_LENGTH_M, TANK_WIDTH_M,
    HORIZONTAL_DIFFUSIVITY,
)


def _tank_bounds(origin_lat: float = TANK_ORIGIN_LAT,
                 origin_lon: float = TANK_ORIGIN_LON,
                 length_m: float = TANK_LENGTH_M,
                 width_m: float = TANK_WIDTH_M):
    """수조 경계를 (lat_min, lat_max, lon_min, lon_max) 로 반환."""
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(origin_lat)))
    return (
        origin_lat,
        origin_lat + width_m  * lat_per_m,
        origin_lon,
        origin_lon + length_m * lon_per_m,
    )


class TankDriftModel(OceanDrift):
    """
    수조 검증용 OpenDrift 모델.

    경계 처리 전략:
        1) 반사 경계: 2*경계 - 현재위치 (벽 충돌 물리 근사)
        2) 2차 안전망: 반사 후에도 초과 시 클램프
        이중 처리로 어떤 타임스텝 크기에서도 이탈 방지.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        (self._lat_min, self._lat_max,
         self._lon_min, self._lon_max) = _tank_bounds()

    def update(self):
        """매 time_step마다 OpenDrift가 호출. 이류+확산 후 경계 반사 적용."""
        super().update()
        self._apply_tank_boundary()

    def _apply_tank_boundary(self):
        """
        수조 벽 충돌: 반사 후 클램프 2단계.
        클램프만 쓰면 파티클이 벽면에 쌓이는 artifact 발생.
        """
        lon = self.elements.lon
        lat = self.elements.lat

        # X 경계 (경도, 수조 길이 방향)
        over_right = lon > self._lon_max
        under_left = lon < self._lon_min
        lon[over_right] = 2 * self._lon_max - lon[over_right]
        lon[under_left] = 2 * self._lon_min - lon[under_left]

        # Y 경계 (위도, 수조 폭 방향)
        over_top = lat > self._lat_max
        under_bot = lat < self._lat_min
        lat[over_top] = 2 * self._lat_max - lat[over_top]
        lat[under_bot] = 2 * self._lat_min - lat[under_bot]

        # 2차 안전망: 반사 후에도 초과 시 클램프
        self.elements.lon = np.clip(lon, self._lon_min, self._lon_max)
        self.elements.lat = np.clip(lat, self._lat_min, self._lat_max)

    @staticmethod
    def apply_tank_config(model: 'TankDriftModel') -> None:
        """
        수조 시뮬레이션에 필요한 설정을 일괄 적용.
        heatmap_pipeline과 test_boundary 양쪽에서 호출.

        OpenDrift 1.14+ 변경사항:
          - drift:deactivate_stranded_elements → 제거됨
          - 대체: general:use_auto_landmask=False + fallback land_binary_mask=0
        """
        model.set_config('general:use_auto_landmask', False)
        model.set_config('environment:fallback:land_binary_mask', 0)
        model.set_config('drift:horizontal_diffusivity', HORIZONTAL_DIFFUSIVITY)
