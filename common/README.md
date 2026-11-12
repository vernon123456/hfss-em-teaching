# common/ — 共享模块

教学案例的共用基础设施，不对应具体物理案例。

## `env_bootstrap.py`

为 PyAEDT 脚本注入 `ANSYSEM_ROOT261` / `AWP_ROOT261`。各案例脚本在顶部已内联相同逻辑，本模块将其集中，便于统一修改安装路径。

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
from env_bootstrap import ensure_env
ensure_env()
from ansys.aedt.core import Hfss
```

如需适配你的机器，修改模块顶部的 `DEFAULT_ANSYSEM_ROOT` / `DEFAULT_AWP_ROOT`，或通过系统环境变量覆盖（二者优先于默认值）。

## 目录约定

- 每个案例自含 `README.md` + canonical 脚本 + `results/`（CSV/PNG/样例 `.eig`）。
- 工程二进制（`.aedt` 等）与求解缓存不入库，重跑脚本即可再生。
- 探索性脚本与中间结果见根目录 `dev_history/`。
