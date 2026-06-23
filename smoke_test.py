"""
설치 검증 스크립트.
Raspberry Pi 5 + Windows 양쪽에서 모두 통과해야 한다.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print(f"파이썬 버전: {sys.version}")

try:
    import opendrift
    from importlib.metadata import version
    od_ver = version('opendrift')
    print(f"[확인] OpenDrift: {od_ver}")
except ImportError as e:
    print(f"[실패] OpenDrift: {e}")
    print("  -> conda install -c conda-forge opendrift")
    sys.exit(1)

try:
    import h3
    print(f"[확인] h3: {h3.__version__}")
    cell = h3.geo_to_h3(37.5, 126.7, 15)
    print(f"  검증 셀 인덱스: {cell}")
except ImportError as e:
    print(f"[실패] h3: {e}")
    print("  -> pip install h3==3.7.7")
    sys.exit(1)
except AttributeError:
    print("[실패] h3 버전 오류: geo_to_h3 없음. h3==3.7.7 사용 중인지 확인")
    print("  h3 4.x는 latlng_to_cell() 사용 — 이 프로젝트는 3.x API 사용")
    sys.exit(1)

try:
    from opendrift.models.oceandrift import OceanDrift
    print("[확인] OceanDrift 불러오기 성공")
except ImportError as e:
    print(f"[실패] OceanDrift: {e}")
    sys.exit(1)

try:
    import numpy as np
    import scipy
    import matplotlib
    print(f"[확인] numpy: {np.__version__}")
    print(f"[확인] scipy: {scipy.__version__}")
    print(f"[확인] matplotlib: {matplotlib.__version__}")
except ImportError as e:
    print(f"[실패] 기본 의존성: {e}")
    sys.exit(1)

print("\n=== 모든 의존성 설치 확인 완료 ===")
