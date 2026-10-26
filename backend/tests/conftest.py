"""pytest 公共配置：把 backend 根目录加入 sys.path，保证 `import app` 可用。

单独运行 `pytest`（不经 `python -m pytest`）时，pytest 只会把 tests 目录加入
sys.path，这里显式补上 backend 根目录，避免依赖运行方式。
"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
