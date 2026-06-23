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
        """매 time_step마다 OpenDrift가 호출. 이류 → 수동확산 → 경계 반사 순서."""
        super().update()
        self._apply_diffusion()
        self._apply_tank_boundary()

    def _apply_diffusion(self):
        """
        수동 수평 확산.
        OpenDrift config 기반 diffusivity는 수조 스케일(1e-6도 단위)에서
        부동소수점 정밀도 손실로 동작하지 않아 직접 구현.
        """
        n = len(self.elements.lon)
        if n == 0:
            return
        std_m = math.sqrt(2.0 * HORIZONTAL_DIFFUSIVITY)  # dt=1s 기준 m 단위 표준편차
        lat_per_m = 1.0 / 111000.0
        lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(TANK_ORIGIN_LAT)))
        self.elements.lat += np.random.normal(0.0, std_m * lat_per_m, n)
        self.elements.lon += np.random.normal(0.0, std_m * lon_per_m, n)

    @staticmethod
    def _reflect_1d(vals: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
        """
        모듈로 반사: 몇 번을 벽 밖으로 나가도 정확히 반사.
        period = 2*(vmax-vmin) 기준으로 삼각파 접기.
        단순 2*boundary 공식은 한 스텝 이동거리 > 수조 크기 시 벽에 쌓임.
        """
        span = vmax - vmin
        v = vals - vmin                 # [0, ...] 기준으로 이동
        v = v % (2 * span)              # 주기 2L 로 wrap
        over = v > span
        v[over] = 2 * span - v[over]    # 후반부 반사
        return v + vmin

    def _apply_tank_boundary(self):
        self.elements.lon = self._reflect_1d(
            self.elements.lon, self._lon_min, self._lon_max)
        self.elements.lat = self._reflect_1d(
            self.elements.lat, self._lat_min, self._lat_max)

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
        # 수동 확산(_apply_diffusion)을 사용하므로 OpenDrift 내부 확산은 비활성화
        model.set_config('drift:horizontal_diffusivity', 0)
