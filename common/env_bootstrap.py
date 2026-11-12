"""共享环境引导：为 PyAEDT 脚本注入 Ansys AEDT 安装路径。

每个案例脚本在启动 HFSS 前都需要这些变量；独立 Python 进程不继承安装器
环境变量，缺失时会报 "AEDT is not installed"。本模块集中管理，避免各脚本
重复硬编码。

用法（在案例脚本顶部）：
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
    from env_bootstrap import ensure_env
    ensure_env()
    from ansys.aedt.core import Hfss
    ...
"""

import os

# AEDT 2026.1 (v261) 默认安装根。如你的安装路径不同，修改这里或通过环境变量覆盖。
DEFAULT_ANSYSEM_ROOT = r"D:\software\ANSYS Inc\v261\AnsysEM"
DEFAULT_AWP_ROOT = r"D:\software\ANSYS Inc\v261"


def ensure_env(ansysem_root=None, awp_root=None):
    """确保 ANSYSEM_ROOT261 / AWP_ROOT261 已注入当前进程。

    返回(bool)：本次是否新设置了变量（原未设置）。
    """
    changed = False
    if "ANSYSEM_ROOT261" not in os.environ:
        os.environ["ANSYSEM_ROOT261"] = ansysem_root or DEFAULT_ANSYSEM_ROOT
        changed = True
    if "AWP_ROOT261" not in os.environ:
        os.environ["AWP_ROOT261"] = awp_root or DEFAULT_AWP_ROOT
        changed = True
    # PyAEDT 通过版本号定位安装；2026.1 对应 v261。
    os.environ.setdefault("PYAEDT_VERSION", "2026.1")
    return changed


if __name__ == "__main__":
    print("env set:", ensure_env())
    print("ANSYSEM_ROOT261 =", os.environ.get("ANSYSEM_ROOT261"))
    print("AWP_ROOT261     =", os.environ.get("AWP_ROOT261"))
