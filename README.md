# HFSS 表面波与周期结构教学案例集

一组基于 Ansys HFSS Eigenmode 求解器的表面波（surface wave）/ 周期结构教学示例。每个案例聚焦一个可独立运行、可复现的物理或方法点，从最小闭环逐步进阶到六边形晶格的能带表征。

## 案例索引

| # | 目录 | 主题 | 关键结果 |
|---|------|------|----------|
| 1 | `01_scalar_impedance_surface/` | 标量阻抗面最小案例（色散验证闭环） | 7 点最大误差 0.425%，平均 0.149% |
| 2 | `02_patch_unit_cell/` | 接地方贴片单元（Fong 2010）反解 Zs | Xs 239.8→147.3 Ω（g 0.2→1.0 mm） |
| 3 | `03_tensor_sliced_patch/` | 切片方贴片张量阻抗面 | 主轴角随 θ_s 单调；理想边界 5 方向误差 ≤0.504% |
| 4 | `04_modulated_supercell/` | 调制阻抗超胞带隙（8 单元 gap 正弦） | M=0→0.3 区边界带隙 0.0010→0.0638 GHz |
| 5 | `05_slotted_circular_patch/` | 开槽圆贴片单元 | 主轴角端点偏差 ≤2.2°，优于方切片 |
| 6 | `06_hexagonal_lattice/` | 六边形排列（矩形超胞）能带 | M 点严格闭合 0.002757 GHz |

每个案例目录下有独立的 `README.md`，含模型参数、求解设置、运行步骤、预期结果与已知限制。

## 环境要求

- Ansys AEDT 2026.1（v261），**必须 GUI 模式启动**。
- PyAEDT 1.4.0（本工作区验证环境：`C:/Users/Verno/.workbuddy/binaries/python/envs/pyaedtmcp/Scripts/python.exe`，含 matplotlib）。
- 脚本需注入 `ANSYSEM_ROOT261` 与 `AWP_ROOT261`（见 `common/env_bootstrap.py`）；独立 Python 进程不继承安装器变量，缺失会报「AEDT is not installed」。

## 运行方式

```bash
# 以案例 1 为例
cd 01_scalar_impedance_surface
python build_and_run.py
```

脚本会在首次运行时自动注入环境、新建/打开工程并构建几何（design 缺失时由 `build()` 自建），求解后将本征模态导出到 `results/`。单相位点约 18–25 s，整案例通常数分钟内完成。

## 关于产物

- 工程二进制（`.aedt` / `.aedtresults` / `.pyaedt`）与求解缓存（`.eig` 批量导出、`*.log`）**未纳入版本库**，均可在重跑脚本后再生（见 `.gitignore`）。
- 每个案例 `results/` 下保留少量关键 CSV/PNG 与 1 个 `.eig` 样例，便于离线查看结果。
- 探索性脚本与中间结果归档于 `dev_history/`，不在教学主线内。

## 引用与术语

- 案例 2/3 基于 C. Caloz & T. Itoh 系列工作（Fong & Itoh, *IEEE TAP* 58(9), 2010；US 7911407）。
- 案例 6 的不可约布里渊区（IBZ）相位关系与复模态处理参考 *IEEE TMTT* 73(9), 2025（MMTMM 本征解）。
- 术语沿用原始论文；未在其他文献核验的表述在案例 README 中标注 `[术语未验证]`。

## 许可

MIT License，见 `LICENSE`。
