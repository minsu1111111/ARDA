"""
설치 검증 스크립트.
Jetson Nano + Windows 양쪽에서 모두 통과해야 한다.
"""
import sys

print(f"Python: {sys.version}")

try:
    import opendrift
    print(f"OpenDrift OK: {opendrift.__version__}")
except ImportError as e:
    print(f"[FAIL] OpenDrift: {e}")
    print("  -> pip install opendrift==1.8.2")
    sys.exit(1)

try:
    import h3
    print(f"h3 OK: {h3.__version__}")
    cell = h3.geo_to_h3(37.5, 126.7, 15)
    print(f"  h3.geo_to_h3(37.5, 126.7, 15) = {cell}")
except ImportError as e:
    print(f"[FAIL] h3: {e}")
    print("  -> pip install h3==3.7.7")
    sys.exit(1)
except AttributeError:
    print("[FAIL] h3 버전 오류: geo_to_h3 없음. h3==3.7.7 사용 중인지 확인")
    print("  h3 4.x API: h3.latlng_to_cell() — 이 프로젝트는 3.x API 사용")
    sys.exit(1)

try:
    from opendrift.models.oceandrift import OceanDrift
    print("OceanDrift import OK")
except ImportError as e:
    print(f"[FAIL] OceanDrift: {e}")
    sys.exit(1)

try:
    import numpy as np
    import scipy
    import matplotlib
    print(f"numpy OK: {np.__version__}")
    print(f"scipy OK: {scipy.__version__}")
    print(f"matplotlib OK: {matplotlib.__version__}")
except ImportError as e:
    print(f"[FAIL] 기본 의존성: {e}")
    sys.exit(1)

print("\n=== 모든 의존성 설치 확인 완료 ===")
