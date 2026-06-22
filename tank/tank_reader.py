"""
1m × 0.5m 수조용 합성 유속 Reader.
OpenDrift 1.14+ API 기준: BaseReader + ContinuousReader 이중 상속.
필수 속성(proj4, xmin/xmax, start_time 등)을 super().__init__() 이전에 설정.
펌프 센서가 붙으면 update_flow()로 실시간 유속 교체 가능.
"""

import math

import numpy as np
from opendrift.readers.basereader import BaseReader, ContinuousReader

from config import TANK_ORIGIN_LAT, TANK_ORIGIN_LON, TANK_LENGTH_M, TANK_WIDTH_M


def _lat_per_m() -> float:
    return 1.0 / 111000.0


def _lon_per_m(ref_lat: float) -> float:
    return 1.0 / (111000.0 * math.cos(math.radians(ref_lat)))


class TankReader(BaseReader, ContinuousReader):
    """
    수조 전용 OpenDrift Reader.
    공간적으로 균일한 유속(단일 펌프 모델)을 가정한다.

    좌표계:
        수조 남서 모서리 = (TANK_ORIGIN_LAT, TANK_ORIGIN_LON)
        x방향(경도) = TANK_LENGTH_M
        y방향(위도) = TANK_WIDTH_M

    OpenDrift 1.14+ 필수 패턴:
        1) BaseReader, ContinuousReader 이중 상속
        2) proj4 / xmin/xmax/ymin/ymax / start_time 등을 super().__init__() 이전에 설정
        3) start_time=None → 항상 유효(ContinuousReader 동작)
    """

    def __init__(self,
                 origin_lat: float = TANK_ORIGIN_LAT,
                 origin_lon: float = TANK_ORIGIN_LON,
                 tank_length_m: float = TANK_LENGTH_M,
                 tank_width_m: float = TANK_WIDTH_M,
                 u_pump_ms: float = 0.05,
                 v_pump_ms: float = 0.01):
        """
        Parameters
        ----------
        origin_lat/lon : 수조 남서 모서리 가짜 GPS 좌표
        tank_length_m  : x방향(경도) 길이 (m)
        tank_width_m   : y방향(위도) 폭 (m)
        u_pump_ms      : x_sea_water_velocity (m/s)
        v_pump_ms      : y_sea_water_velocity (m/s)
        """
        # ── super().__init__() 이전에 모든 필수 속성 설정 ─────────────
        self._u = float(u_pump_ms)
        self._v = float(v_pump_ms)
        self.name = 'TankReader'

        # 가짜 위경도 경계 계산
        lat_ext = tank_width_m  * _lat_per_m()
        lon_ext = tank_length_m * _lon_per_m(origin_lat)

        self.lat_min = origin_lat
        self.lat_max = origin_lat + lat_ext
        self.lon_min = origin_lon
        self.lon_max = origin_lon + lon_ext

        # BaseReader 필수: 공간 범위 (latlong 좌표계에서 x=lon, y=lat)
        self.xmin = self.lon_min
        self.xmax = self.lon_max
        self.ymin = self.lat_min
        self.ymax = self.lat_max

        # BaseReader 필수: 투영 정보
        self.proj4 = '+proj=latlong +datum=WGS84'
        self.proj = None  # BaseReader.__init__이 proj4로부터 자동 생성

        # ContinuousReader 패턴: start_time=None → 시간 검증 생략, 항상 유효
        self.start_time = None
        self.end_time = None
        self.time_step = None
        self.times = None

        # 제공하는 변수 목록
        self.variables = ['x_sea_water_velocity', 'y_sea_water_velocity']

        # ── 이 아래에서 super().__init__() 호출 ───────────────────────
        super().__init__()

    def get_variables(self, requested_variables, time=None,
                      x=None, y=None, z=None):
        """
        요청 파티클 위치에 균일 유속 배열 반환.
        x=경도 배열, y=위도 배열 (OpenDrift 내부 규약).
        """
        n = len(x) if x is not None else 1
        result = {}
        if 'x_sea_water_velocity' in requested_variables:
            result['x_sea_water_velocity'] = np.full(n, self._u, dtype=float)
        if 'y_sea_water_velocity' in requested_variables:
            result['y_sea_water_velocity'] = np.full(n, self._v, dtype=float)
        return result

    def update_flow(self, u_ms: float, v_ms: float) -> None:
        """실시간 펌프 센서값으로 유속 갱신 (30초 주기 호출 권장)."""
        self._u = float(u_ms)
        self._v = float(v_ms)
