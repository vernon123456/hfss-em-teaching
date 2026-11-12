# Grounded patch unit cell 与 HFSS Eigenmode 等效表面阻抗提取

## 结论

把上一案例的理想 `Impedance` sheet 换成 Fong 2010 的可加工方贴片单元，用 HFSS Eigenmode 色散反解 17 GHz 的 `effective surface reactance`。等效电抗随 gap 单调递减，从 g=0.2 mm 的 **239.8 Ω** 降到 g=1.0 mm 的 **147.3 Ω**。小 gap 与两组文献端点吻合到 ±2.5%，大 gap 系统性偏低 8.5% 到 9.8%。独立闭环中，理想阻抗面 HFSS 与闭式解最大偏差 **0.0089%**。

## 口径核验（第 1 步结论，修正了开工前的假设）

论文正文列出三种 Z 提取法，采用「只需计算表面波频率或波矢」的色散反解法，并明确它与场积分等价。反射系数反演是第三种方法，论文未采用。因此本案例的 Eigenmode 反解与原文方法一致，开工前标记的「口径不一致」风险解除。

| 项 | 原文表述 | 本案例处理 |
|---|---|---|
| 工作点 | 固定 **72 deg/cell** 相位差，17 GHz，λ0=17 mm | 固定 **17 GHz**，插值 f(px) 求 φ* |
| 扫参 | 扫 gap 得 Z(g) | 每个 g 扫 7 个相位，再插值 |
| 数值 | g 从 1.0 到 0.2 mm，Z 从 161j 到 234j Ω | 见下表 |

固定相位与固定频率在色散曲线上取的是不同点。φ*=72.6 deg 出现在 g=0.2 mm，与论文 72 deg 工作点吻合；g 增大时 φ* 降到 65.8 deg，这是大 gap 偏差的候选原因之一（推断）。

## 术语核验

| 表述 | 映射 | 来源与状态 |
|---|---|---|
| 等效表面阻抗 | `surface impedance` Zs = Rs + jXs（Ω/square） | [Ansys Help, Impedance Boundaries](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Content/HFSS/ImpedanceBoundaries.htm)，**已核验** |
| 色散反解 | `Zs = jη0√((β/k0)²−1)`，`Xs = Im{Zs}` | [Adv. Electron. Mater. 式(4)(5)](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aelm.70606)、[arXiv:2611.08166 式(28)](https://arxiv.org/html/2611.08166v1) 横向谐振条件、[EPJ Appl. Metamater. 2019](https://www.sciengine.com/EPJ-AM/doi/10.1051/epjam/2019011)，**已核验** |
| 中文「实物贴片单元」 | 描述性短语，对应 `array of sub-wavelength metallic patches on a grounded dielectric substrate` | [Fong 2010 摘要](https://doi.org/10.1109/TAP.2010.2055812)，英文**已核验**；中文 `[术语未验证]`，不作标题与定义 |

## 模型

| 参数 | 值 | 依据 |
|---|---|---|
| 单元周期 p | 3 mm | Fong 2010 正文 |
| 介质 | h=1.57 mm，εr=2.2（Rogers Duroid 5880） | Fong 2010 正文 |
| 贴片 | 方片边长 a = p − g，PEC sheet，居中 | `g = d − a`（Opt. Express 2015 图 2） |
| 底面 / 顶面 | PEC 地板 / PEC 盖，H=30 mm | Eigenmode 禁辐射边界，顶盖按 αz 取足 |
| 周期边界 | 4 对 Lattice Pair，x 方向 `px`，y 方向 0 deg | 介质与空气共面侧壁需分组配对 |
| 求解 | `HFSSEigen`，MinFreq 10 GHz，NumModes 6，MaxDeltaFreq 1% | [Ansys Help, Adding an Eigenmode Setup](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/AddinganEigenmodeSetup.htm) |

35 个求解点（5 个 gap × 7 个相位，55 到 85 deg 步长 5 deg），总计约 10 分钟。结果只走官方 `ExportEigenmodes`（[Help](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportEigenmodes.htm)），每点求解后立即保存工程。

## 结果

| g (mm) | φ* (deg) | Xs (Ω) |
|---|---|---|
| 0.2 | 72.598 | 239.816 |
| 0.4 | 69.116 | 197.081 |
| 0.6 | 67.505 | 174.679 |
| 0.8 | 66.570 | 160.515 |
| 1.0 | 65.757 | 147.303 |

与文献端点的偏差：

| 对照点 | HFSS (Ω) | 偏差 |
|---|---|---|
| g=0.2 vs Fong 234 | 239.816 | +2.49% |
| g=1.0 vs Fong 161 | 147.303 | -8.51% |
| g=0.2 vs Opt. Express 245.70 | 239.816 | -2.39% |
| g=1.0 vs Opt. Express 163.38 | 147.303 | -9.84% |

反解只用 mode 1。`Xs_by_mode.csv` 显示 mode 2 仅在 g=0.2 给出 130.6 Ω，mode 3 到 6 的 f(px) 在 17 GHz 无交叉或 β≤k0，未采用。这属于模式筛选结果，不是全部模式都能反解。

## 独立闭环（避免循环论证）

只用 17 GHz 单点反解再代回同一公式属于恒等验证。因此用 5 个 Xs 的平均值 **183.879 Ω** 新建理想阻抗面 HFSS 模型，重跑同一相位段，得到整条 HFSS 色散曲线。

| 检验 | 结果 |
|---|---|
| 理想 sheet HFSS vs 闭式解 | 最大 0.0089%，平均 0.0059% |
| 实物单元 5 条曲线 | 分布在理想直线两侧，随 g 单调移动 |

`ideal_compare.png` 是主对照图。理想曲线穿过实物曲线簇中部，说明实物单元的等效阻抗随 g 变化，且低频段偏离常数阻抗模型。由于理想模型取平均 Xs，它不代表任一具体 g 的等效值，这是刻意的折中（逐个 g 重跑需再 35 个求解点）。

## 偏差与失败样本

大 gap 系统性偏低 8.5% 到 9.8%，未定位根因。已排除与未排除的候选：

| 候选 | 状态 |
|---|---|
| PEC 顶盖 | 按 αz = k0·Xs/η0 估算，g=1.0 时 e^(−2αH) ≈ 2.4e−4，**基本排除** |
| 网格收敛 | MaxDeltaFreq 1%、MinimumPasses 2，贴片边缘场集中，**未验证**（推断） |
| 工作点口径 | 论文固定 72 deg，本案例固定 17 GHz，**未验证**（推断） |
| 模式识别 | 高 g 时 mode 1 可能混有腔模，未勾 Save Fields 看场，**未验证**（推断） |

其他已知限制：纯仿真无实测；εr 取常数，未含介质色散与损耗；全部结构无损，`.eig` 的 Q 列为 0；只算 x 方向传播；未做独立网格收敛研究。

## 复现

```
python patch_unitcell.py                              # 35 点全流程，约 10 min
RUN_MODE=post python patch_unitcell.py                # 只重算表与图
python ideal_check.py                                 # 7 点独立闭环，约 4 min
GAPS_OVERRIDE=0.6 PHASES_OVERRIDE=70 python patch_unitcell.py   # 单点最小闭环
MODE_INDEX=2 RUN_MODE=post python patch_unitcell.py   # 换模式分支
```

解释器 `C:/Users/Verno/.workbuddy/binaries/python/envs/pyaedtmcp/Scripts/python.exe`，AEDT 2026.1 GUI 模式。脚本内注入 `ANSYSEM_ROOT261` 与 `AWP_ROOT261`。`eig_points.csv` 增量写入，中断后重跑会跳过已完成点。

## 文件清单

| 文件 | 用途 |
|---|---|
| `patch_unitcell.py` / `patch_unitcell.aedt` | 主流程脚本与工程 |
| `ideal_check.py` / `ideal_sheet.aedt` | 独立闭环脚本与工程 |
| `eig_points.csv` / `eig/` | 35 点原始本征频率与官方 `.eig` |
| `Z_vs_g.csv` / `Z_vs_g.png` | Z(g) 主结果与文献端点对照图 |
| `Xs_by_mode.csv` / `ideal_dispersion.csv` | 各模式反解值、理想模型色散 |
| `ideal_compare.png` / `dispersion_by_g.png` | 独立闭环图、辅助色散图 |
| `run.log` / `ideal_check.log` | 运行留痕 |

原案例 `scalar_impedance_eigenmode/` 完全未改动，可作回滚基线。

## 来源与确定性

一手（期刊与官方）：[Fong 等, IEEE TAP 58(10), 3212–3221 (2010)](https://doi.org/10.1109/TAP.2010.2055812)、[Opt. Express 23, 7593 (2015)](https://doi.org/10.1364/OE.23.007593)、[Adv. Electron. Mater. 式(4)(5)](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aelm.70606)、[arXiv:2611.08166 式(28)](https://arxiv.org/html/2611.08166v1)、[EPJ Appl. Metamater. 2019](https://www.sciengine.com/EPJ-AM/doi/10.1051/epjam/2019011)、[Ansys Help, Coupled Lattice Pair](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v261/en/Subsystems/HFSS/Content/HFSS/AssigningCoupledLatticePairBoundaries.htm)。

IEEE Xplore 全文需订阅，ResearchGate 直接访问返回访问限制页。Fig.3 的 161j~234j Ω、72 deg/cell、式(5) 描述来自搜索引擎索引的正文片段（[链接](https://www.researchgate.net/publication/224151557_Scalar_and_Tensor_Holographic_Artificial_Impedance_Surfaces)），标 **待核验**，未取得 IEEE PDF 原件。另一片段把该图标为 Fig.2，图号存疑。

确定性：HFSS 能力、反解公式、理想闭环误差、Z(g) 数值与偏差 **已核验**（本会话实测或官方文档）；论文端点数值 **权威二手转录，待核验原文**；大 gap 偏差根因 **推断**；顶盖影响估算 **推断**（由 αz 公式算得）。
