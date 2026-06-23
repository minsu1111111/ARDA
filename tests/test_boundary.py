"""
TankDriftModel 경계 조건 단위 테스트.
파티클이 수조 밖으로 탈출하지 않는지 검증.
의존성: opendrift
"""

import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime, timedelta

import numpy as np
from tank.tank_model import TankDriftModel
from tank.tank_reader import TankReader
from config import TANK_ORIGIN_LAT, TANK_ORIGIN_LON, TANK_LENGTH_M, TANK_WIDTH_M


def _bounds():
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(TANK_ORIGIN_LAT)))
    return (
        TANK_ORIGIN_LAT,
        TANK_ORIGIN_LAT + TANK_WIDTH_M  * lat_per_m,
        TANK_ORIGIN_LON,
        TANK_ORIGIN_LON + TANK_LENGTH_M * lon_per_m,
    )


def test_no_particles_escape():
    """10초 실행 후 모든 파티클이 수조 경계 내부에 있는지 확인."""
    lat_min, lat_max, lon_min, lon_max = _bounds()

    entry_lat = lat_min + (lat_max - lat_min) * 0.9
    entry_lon = lon_min + (lon_max - lon_min) * 0.9

    reader = TankReader(u_pump_ms=0.20, v_pump_ms=0.10)
    model = TankDriftModel(loglevel=50)
    model.add_reader(reader)
    TankDriftModel.apply_tank_config(model)

    model.seed_elements(
        lon=entry_lon, lat=entry_lat,
        number=50, radius=0,
        time=datetime(2026, 6, 22, 9, 0, 0),
    )
    model.run(
        duration=timedelta(seconds=10),
        time_step=timedelta(seconds=1),
    )

    final_lats = np.array(model.elements.lat)
    final_lons = np.array(model.elements.lon)

    out_lat = int(np.sum((final_lats < lat_min) | (final_lats > lat_max)))
    out_lon = int(np.sum((final_lons < lon_min) | (final_lons > lon_max)))

    assert out_lat == 0, f"[실패] 위도 초과 파티클: {out_lat}개"
    assert out_lon == 0, f"[실패] 경도 초과 파티클: {out_lon}개"
    print("[통과] 파티클 경계 이탈 없음 검증")


def test_deactivate_stranded_disabled():
    """파티클이 비활성화되지 않고 모두 살아있는지 확인."""
    lat_min, lat_max, lon_min, lon_max = _bounds()

    entry_lat = (lat_min + lat_max) / 2
    entry_lon = (lon_min + lon_max) / 2

    reader = TankReader()
    model = TankDriftModel(loglevel=50)
    model.add_reader(reader)
    TankDriftModel.apply_tank_config(model)

    model.seed_elements(
        lon=entry_lon, lat=entry_lat,
        number=100, radius=0,
        time=datetime(2026, 6, 22, 9, 0, 0),
    )
    model.run(
        duration=timedelta(seconds=30),
        time_step=timedelta(seconds=1),
    )

    active = model.num_elements_active()
    loss_rate = 1.0 - active / 100
    assert loss_rate < 0.05, (
        f"[실패] 파티클 손실률 {loss_rate*100:.1f}% — landmask 설정 확인 필요"
    )
    print(f"[통과] 파티클 비활성화 방지 검증: 활성 {active}/100개")


if __name__ == '__main__':
    test_no_particles_escape()
    test_deactivate_stranded_disabled()
    print("\n=== 경계 조건 단위 테스트 전체 통과 ===")
