# 강민수(수조) + 이다빈(한강) 공통 상수
# 수정 시 반드시 상대방에게 알릴 것
# ENVIRONMENT 값은 로컬에서만 변경 — 절대 커밋 금지

# ====== 공통 (독자 수정 금지) ======
N_PARTICLES = 500
TIME_STEP_S = 1           # seconds
TOTAL_TIME_S = 300        # 5분 (골든타임)
WAYPOINT_THRESHOLD = 0.005   # 0.5% 이상만 Waypoint 후보
PARTICLE_FILTER_UPDATE_INTERVAL = 30  # seconds

# 파티클 배열 공통 키 (두 사람 모두 동일하게 사용)
PARTICLE_LAT_KEY = 'lat'
PARTICLE_LON_KEY = 'lon'
PARTICLE_AGE_KEY = 'age_seconds'

# dynamics_fn 시그니처: (t: float, x_lon: float, y_lat: float) -> (u: float, v: float)

# ====== 환경 분기 (로컬 전용) ======
ENVIRONMENT = 'tank'   # 'tank' | 'han_river'

if ENVIRONMENT == 'tank':
    # 강민수 — 수조 검증 환경
    H3_RESOLUTION          = 15      # 엣지 ~0.5m, 수조에 10~15개 셀
    HORIZONTAL_DIFFUSIVITY = 0.02    # sqrt(2*0.02*300)≈3.5m → 수조 내 충분한 퍼짐
    TANK_ORIGIN_LAT        = 37.500000
    TANK_ORIGIN_LON        = 126.700000
    TANK_LENGTH_M          = 1.0     # x방향 (경도)
    TANK_WIDTH_M           = 0.5     # y방향 (위도)
    ENTRY_RADIUS_M         = 0.05    # 입수 반경 5cm

elif ENVIRONMENT == 'han_river':
    # 이다빈 — 한강 본 환경
    H3_RESOLUTION          = 10      # 엣지 ~150m
    HORIZONTAL_DIFFUSIVITY = 0.1     # 맑은 날 기준
    TANK_ORIGIN_LAT        = None    # 실제 GPS 사용
    TANK_ORIGIN_LON        = None
    TANK_LENGTH_M          = None
    TANK_WIDTH_M           = None
    ENTRY_RADIUS_M         = 10.0    # 한강 입수 반경 10m

else:
    raise ValueError(f"알 수 없는 ENVIRONMENT 값: {ENVIRONMENT!r}")
