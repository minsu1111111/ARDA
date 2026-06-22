"""
TankReader 단위 테스트.
의존성: opendrift, numpy
"""

import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from tank.tank_reader import TankReader
from config import TANK_ORIGIN_LAT, TANK_ORIGIN_LON, TANK_LENGTH_M, TANK_WIDTH_M


def test_get_variables_shape():
    """n개 파티클 요청 시 n개 유속값 반환 확인."""
    reader = TankReader(u_pump_ms=0.05, v_pump_ms=0.01)
    fake_x = np.array([126.700005, 126.700008, 126.700010])
    fake_y = np.array([37.500002,  37.500003,  37.500004])

    result = reader.get_variables(
        ['x_sea_water_velocity', 'y_sea_water_velocity'],
        x=fake_x, y=fake_y,
    )
    assert len(result['x_sea_water_velocity']) == 3, "배열 크기 불일치"
    assert len(result['y_sea_water_velocity']) == 3, "배열 크기 불일치"
    print("[PASS] test_get_variables_shape")


def test_get_variables_values():
    """반환 유속값이 설정값과 일치하는지 확인."""
    reader = TankReader(u_pump_ms=0.07, v_pump_ms=0.02)
    result = reader.get_variables(
        ['x_sea_water_velocity', 'y_sea_water_velocity'],
        x=np.array([126.7]), y=np.array([37.5]),
    )
    assert np.allclose(result['x_sea_water_velocity'], 0.07), "u 값 오류"
    assert np.allclose(result['y_sea_water_velocity'], 0.02), "v 값 오류"
    print("[PASS] test_get_variables_values")


def test_update_flow():
    """update_flow() 호출 후 유속이 갱신되는지 확인."""
    reader = TankReader(u_pump_ms=0.05, v_pump_ms=0.01)
    reader.update_flow(0.10, 0.03)
    result = reader.get_variables(
        ['x_sea_water_velocity'],
        x=np.array([126.7]), y=np.array([37.5]),
    )
    assert np.allclose(result['x_sea_water_velocity'], 0.10), "update_flow 미반영"
    print("[PASS] test_update_flow")


def test_bounding_box():
    """Reader의 경계 상자가 수조 크기에 맞게 계산되는지 확인."""
    reader = TankReader()
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(TANK_ORIGIN_LAT)))

    expected_lat_max = TANK_ORIGIN_LAT + TANK_WIDTH_M  * lat_per_m
    expected_lon_max = TANK_ORIGIN_LON + TANK_LENGTH_M * lon_per_m

    assert abs(reader.lat_max - expected_lat_max) < 1e-9, "lat_max 계산 오류"
    assert abs(reader.lon_max - expected_lon_max) < 1e-9, "lon_max 계산 오류"
    print("[PASS] test_bounding_box")


if __name__ == '__main__':
    test_get_variables_shape()
    test_get_variables_values()
    test_update_flow()
    test_bounding_box()
    print("\n=== TankReader 단위 테스트 전체 통과 ===")
