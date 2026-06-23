"""
수조 전체 파이프라인.
TankReader → TankDriftModel → H3 빈닝 → matplotlib 시각화 → JSON 출력.
인터넷 없이 오프라인으로 동작 (folium 미사용).
"""

import json
import math
import os
from datetime import datetime, timedelta

import matplotlib.font_manager as fm
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

# 한국어 폰트 설정 (Windows: 맑은 고딕, Linux/Pi: NanumGothic 우선)
def _setup_korean_font():
    candidates = ['Malgun Gothic', 'NanumGothic', 'NanumBarunGothic', 'AppleGothic']
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams['font.family'] = font
            break
    plt.rcParams['axes.unicode_minus'] = False

_setup_korean_font()

from config import (
    ENTRY_RADIUS_M,
    N_PARTICLES, TANK_LENGTH_M, TANK_ORIGIN_LAT, TANK_ORIGIN_LON,
    TANK_WIDTH_M, TIME_STEP_S, TOTAL_TIME_S, WAYPOINT_THRESHOLD,
    H3_RESOLUTION,
)
from shared.h3_utils import (
    filter_waypoints, particles_to_h3_heatmap, validate_h3_coverage,
)
from shared.output_schema import build_output_json
from tank.tank_model import TankDriftModel
from tank.tank_reader import TankReader


def _tank_center():
    """수조 중앙 가짜 GPS 좌표 반환."""
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(TANK_ORIGIN_LAT)))
    return (
        TANK_ORIGIN_LAT + (TANK_WIDTH_M  / 2) * lat_per_m,
        TANK_ORIGIN_LON + (TANK_LENGTH_M / 2) * lon_per_m,
    )


def run_tank_simulation(
    entry_lat: float = None,
    entry_lon: float = None,
    u_pump: float = 0.05,
    v_pump: float = 0.01,
    save_path: str = 'results/',
) -> dict:
    """
    수조 파이프라인 실행.

    Parameters
    ----------
    entry_lat/lon : 입수 지점 가짜 GPS (None이면 수조 중앙)
    u_pump        : x방향 유속 m/s
    v_pump        : y방향 유속 m/s
    save_path     : 결과 저장 경로

    Returns
    -------
    build_output_json() 형식의 딕셔너리
    """
    os.makedirs(save_path, exist_ok=True)

    if entry_lat is None or entry_lon is None:
        entry_lat, entry_lon = _tank_center()

    # ── 1) Reader + 모델 초기화 ──────────────────────────────────────────
    reader = TankReader(u_pump_ms=u_pump, v_pump_ms=v_pump)

    model = TankDriftModel(loglevel=20)
    model.add_reader(reader)
    TankDriftModel.apply_tank_config(model)

    # ── 2) 파티클 시드 (입수 좌표 중심, 반경 ENTRY_RADIUS_M) ────────────
    radius_deg = ENTRY_RADIUS_M / 111000.0
    model.seed_elements(
        lon=entry_lon,
        lat=entry_lat,
        number=N_PARTICLES,
        radius=radius_deg,
        time=datetime(2026, 6, 22, 9, 0, 0),
    )

    # CHECKPOINT 1: 파티클 수 확인
    initial_count = model.num_elements_total()
    assert initial_count == N_PARTICLES, (
        f"[실패] 파티클 초기화: 기대={N_PARTICLES}, 실제={initial_count}"
    )
    print(f"[체크포인트 1] 파티클 초기화 완료: {initial_count}개")

    # ── 3) 시뮬레이션 실행 ──────────────────────────────────────────────
    model.run(
        duration=timedelta(seconds=TOTAL_TIME_S),
        time_step=timedelta(seconds=TIME_STEP_S),
        time_step_output=timedelta(seconds=10),
        outfile=None,  # NetCDF 저장 비활성화
    )

    final_lons = np.array(model.elements.lon)
    final_lats = np.array(model.elements.lat)

    # CHECKPOINT 2: 경계 조건 검증
    _assert_boundary(final_lats, final_lons)
    print("[체크포인트 2] 경계 조건 통과: 모든 파티클 수조 내부 확인")

    # CHECKPOINT 3: 파티클 보존율
    active_count = model.num_elements_active()
    loss_rate = 1.0 - active_count / N_PARTICLES
    print(f"[체크포인트 3] 활성 파티클: {active_count}/{N_PARTICLES} "
          f"(손실률 {loss_rate*100:.1f}%)")
    if loss_rate > 0.05:
        print("  [경고] 파티클 5% 이상 손실. landmask 설정 확인 필요.")

    # ── 4) H3 빈닝 ──────────────────────────────────────────────────────
    heatmap = particles_to_h3_heatmap(final_lats, final_lons, H3_RESOLUTION)

    # CHECKPOINT 4: H3 커버리지
    assert validate_h3_coverage(heatmap, min_cells=1), \
        "[실패] H3 커버리지 0% — 좌표계 오류 확인"
    print(f"[체크포인트 4] H3 셀 {len(heatmap)}개 생성됨")

    # ── 5) Waypoint 추출 ────────────────────────────────────────────────
    waypoints = filter_waypoints(heatmap, threshold=WAYPOINT_THRESHOLD)
    print(f"[체크포인트 5] 탐색 지점 {len(waypoints)}개 "
          f"(임계값 {WAYPOINT_THRESHOLD*100:.1f}% 이상)")

    # ── 6) 시각화 ────────────────────────────────────────────────────────
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    _visualize(heatmap, final_lats, final_lons, save_path, ts)

    # ── 7) JSON 출력 ─────────────────────────────────────────────────────
    output = build_output_json(
        waypoints=waypoints,
        sim_params={
            'n_particles':  N_PARTICLES,
            'total_time_s': TOTAL_TIME_S,
            'resolution':   H3_RESOLUTION,
            'entry_lat':    entry_lat,
            'entry_lon':    entry_lon,
            'u_pump_ms':    u_pump,
            'v_pump_ms':    v_pump,
        },
    )
    json_path = os.path.join(save_path, f'waypoints_{ts}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[완료] 결과 저장: {json_path}")

    return output


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────

def _assert_boundary(lats: np.ndarray, lons: np.ndarray) -> None:
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(TANK_ORIGIN_LAT)))
    lat_max = TANK_ORIGIN_LAT + TANK_WIDTH_M  * lat_per_m
    lon_max = TANK_ORIGIN_LON + TANK_LENGTH_M * lon_per_m

    out_lat = int(np.sum((lats < TANK_ORIGIN_LAT) | (lats > lat_max)))
    out_lon = int(np.sum((lons < TANK_ORIGIN_LON) | (lons > lon_max)))
    if out_lat > 0 or out_lon > 0:
        raise AssertionError(
            f"[실패] 경계 조건 위반: 위도 초과={out_lat}개, 경도 초과={out_lon}개"
        )


def _visualize(heatmap: dict, lats: np.ndarray, lons: np.ndarray,
               save_path: str, ts: str) -> None:
    """
    matplotlib 히트맵 시각화 (오프라인 동작).
    좌: 파티클 산포도 + 수조 경계
    우: H3 셀별 확률 막대 그래프
    """
    lat_per_m = 1.0 / 111000.0
    lon_per_m = 1.0 / (111000.0 * math.cos(math.radians(TANK_ORIGIN_LAT)))
    lat_ext = TANK_WIDTH_M  * lat_per_m
    lon_ext = TANK_LENGTH_M * lon_per_m

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 좌: 파티클 산포도
    ax1 = axes[0]
    ax1.scatter(lons, lats, s=2, alpha=0.5, c='royalblue', label=f'파티클 (N={len(lats)})')
    rect = patches.Rectangle(
        (TANK_ORIGIN_LON, TANK_ORIGIN_LAT), lon_ext, lat_ext,
        linewidth=2, edgecolor='red', facecolor='none', label='수조 경계',
    )
    ax1.add_patch(rect)
    ax1.set_xlim(TANK_ORIGIN_LON - lon_ext * 0.1, TANK_ORIGIN_LON + lon_ext * 1.1)
    ax1.set_ylim(TANK_ORIGIN_LAT - lat_ext * 0.1, TANK_ORIGIN_LAT + lat_ext * 1.1)
    ax1.set_title('파티클 최종 분포')
    ax1.set_xlabel('경도 (가짜)')
    ax1.set_ylabel('위도 (가짜)')
    ax1.legend(fontsize=8)

    # 우: H3 확률 막대 그래프
    ax2 = axes[1]
    cells = list(heatmap.keys())
    probs = [heatmap[c]['probability'] for c in cells]
    ax2.bar(range(len(cells)), probs, color='orangered', alpha=0.8)
    ax2.axhline(y=WAYPOINT_THRESHOLD, color='green', linestyle='--',
                label=f'Waypoint 임계값 ({WAYPOINT_THRESHOLD*100:.1f}%)')
    ax2.set_xticks(range(len(cells)))
    ax2.set_xticklabels([c[-6:] for c in cells], rotation=45, ha='right', fontsize=7)
    ax2.set_title('H3 셀별 체류 확률')
    ax2.set_ylabel('확률')
    ax2.legend(fontsize=8)

    plt.tight_layout()
    png_path = os.path.join(save_path, f'heatmap_{ts}.png')
    plt.savefig(png_path, dpi=150)
    plt.close()
    print(f"[시각화] 히트맵 저장: {png_path}")
