# Modulated 8-cell supercell 与 Optimetrics 带隙验证

## 结论

在 `tensor_patch.aedt` 的 design `supercell` 内建 8 单元调制超胞，用 Optimetrics `SweepSupercell` 同时扫调制深度 M 与超胞相位 `phi_sup`，24 个 variation 全部出数。区边界 phi=180° 处最低两分支的分裂随 M 单调增加，从 0.001 GHz 增至 0.064 GHz，M=0 时基本闭合。

| M | f1 (GHz) | f2 (GHz) | 带隙 (GHz) |
|---|---|---|---|
| 0.0 | 11.047386 | 11.048351 | 0.000965 |
| 0.1 | 11.041973 | 11.065960 | 0.023987 |
| 0.2 | 11.045050 | 11.085495 | 0.040445 |
| 0.3 | 11.027736 | 11.091517 | 0.063781 |

带隙定义：同一 phi=180° 下最低两个本征频率之差（f2 − f1）。M=0 的 0.001 GHz 属数值残差，占 0.009%。

## 术语核验

| 表述 | 映射 | 来源与状态 |
|---|---|---|
| 调制阻抗面 | `sinusoidally-modulated reactance surface` | [Casaletti, IEEE TAP 64(8), 2016](https://doi.org/10.1109/TAP.2016.2570251)、[arXiv:1703.01294 式(1)](https://arxiv.org/pdf/1703.01294v1)、[Opt. Express 23, 7593 (2015)](https://doi.org/10.1364/OE.23.007593)，**已核验**；中文 `[术语未验证]` |
| 超胞、折叠色散 | `supercell`、`folded dispersion`、`Brillouin zone boundary` | [Microwave Journal, HFSS PBG 色散](https://www.microwavejournal.com/articles/3044-analysis-of-photonic-bandgap-surfaces-using-ansoft-hfss)（权威二手），中文 `[术语未验证]` |
| 参数扫描 | `Optimetrics Parametric` variable sweep | [Ansys Help, Setting Up a Parametric Analysis](https://ansyshelp.ansys.com/public/views/secured/electronics/v251/en/subsystems/HFSS/Content/Optimetrics/SettingUpaParametricAnalysis.htm)，**已核验** |

## 模型

| 参数 | 值 |
|---|---|
| 单元 | p=3 mm，h=1.57 mm，εr=2.2，PEC 地板与顶盖 H=30 mm |
| 超胞 | N=8，Λ=N·p=24 mm，8 个方贴片 sheet |
| 调制 | `gap_i = gmid*(1 + M*cos(2πi/N))`，gmid=0.6 mm，M 为 AEDT 设计变量 |
| 周期边界 | 4 对 Lattice Pair，x 两对用 `phi_sup`，y 两对用 0 deg |
| 求解 | `HFSSEigen`，MinFreq 10 GHz，NumModes 8，MaxDeltaFreq 1% |
| Optimetrics | M：LIN 0→0.3 step 0.1；phi_sup：LIN 30→180 deg step 30；共 24 点 |

`gap0..gap7` 是引用 M 的表达式变量，几何随 M 自动重建，不需要切换 design 或工程。结果按 `ListVariations` 取回 24 个 variation key，逐个 `ExportEigenmodes(solution, key, path)` 导出 `.eig`。

## 必须说明的限制

1. **带隙测的是最低折叠分支，不是 17 GHz 表面波主模**。NumModes=8 只覆盖约 10 到 16 GHz，区边界处 f1≈11.0 GHz。若要 17 GHz 附近的带隙，需把 NumModes 提到 16 以上并按频率连续性追踪分支，本次未做。
2. **调制是几何调制**。计划原写「用 Z(g) 拟合反求 g_i 使 Z 正弦」，实际改为让 `gap_i` 直接按正弦变化。原因是在 AEDT 表达式中复合三次反演不可靠，且 M 需要保持为单一可扫变量。等效阻抗调制深度与 M 非线性相关，可用 `02_patch_unit_cell/results/Z_vs_g.csv` 在报告里换算，本次未换算。
3. **模式换序**。phi=30°、M=0.3 时 mode2 跳到约 12.0 GHz，与其他 M 的同序号分支不连续。带隙只在 phi=180° 取最低两分支，避开该跳变；跨相位比较必须做模式追踪。
4. **有效介质假设**。p=3 mm、λ0≈17.6 mm，p/λ0≈0.17 已超严格 λ/10，Fong 2010 的 17 GHz 单元同样如此。论文另自报仿真与近场测量需 1 到 1.37 标定且原因未知（[正文片段](https://www.researchgate.net/publication/224151557_Scalar_and_Tensor_Holographic_Artificial_Impedance_Surfaces)）。结论不外推到天线增益。
5. **未做漏波辐射**。Eigenmode 禁辐射边界，Driven/Floquet 分支默认不做，若要辐射角需另建独立工程。

## 失败样本与修正

| 现象 | 处理 |
|---|---|
| 变量名 `g0` 未注册，`Patch0` 引用未定义量，`analyze_setup` 返回 False（4.7 s 静默失败），Optimetrics 报「solved correctly」但 0 个 variation | 改名为 `gap0..gap7`，删除并重建 design；重跑后 M=0 单点 22.7 s 正常出 8 个模式 |
| M 的 sweep Data 用离散串 `'0 0.1 0.185 0.3'`，`export_parametric_results` 只出表头 | 改用已验证的 `LIN` 格式（0/0.1/0.2/0.3），Fong 归一化深度 0.185 落在 0.1 与 0.2 之间可插值 |
| nominal `ExportEigenmodes(solution, "", path)` 在超胞 design 报 `GrpcApiError` | 统一走 `ListVariations` 取 key 后按 variation 导出 |

## 复现

```
RUN_MODE=probe python supercell_scan.py    # 重建后单点退化校验
python supercell_scan.py                   # 24 点 Optimetrics 全扫，约 7 min
RUN_MODE=export python supercell_scan.py   # 只重导出结果
RUN_MODE=post python supercell_scan.py     # 只重算表与图
```

解释器 `C:/Users/Verno/.workbuddy/binaries/python/envs/pyaedtmcp/Scripts/python.exe`，AEDT 2026.1 GUI 模式，脚本内注入 `ANSYSEM_ROOT261` 与 `AWP_ROOT261`。运行前脚本清理残留 `.aedt.lock`。

## 文件清单

| 文件 | 用途 |
|---|---|
| `supercell_scan.py` | 超胞建模、Optimetrics 扫描、导出与后处理 |
| `tensor_patch.aedt`（运行时生成，未提交仓库）| 主工程，含 design `parametric`（保留）与 `supercell` |
| `supercell_results.csv` / `eig_supercell/`（`.eig` 未提交仓库）| 24 个 variation 的频率与官方 `.eig` |
| `bandgap_vs_M.csv` / `bandgap_vs_M.png` | 带隙随 M 的表与图 |
| `dispersion_M.png` | 各 M 的折叠色散曲线 |
| `supercell.log`（运行时生成，未提交仓库）| 运行留痕 |

> 说明：`.aedt` / `.aedtresults/` / `eig*/` / `*.log` 等未提交仓库（见根目录 `.gitignore`），均由脚本运行时生成，可重建。

工程改动前曾在本地备份为 `.workbuddy/backups/tensor_patch/tensor_patch.aedt.20261109-2.bak`（68421 bytes；**本地备份，未纳入仓库**）。`ideal_tensor.aedt` 完全未动。

## 来源与确定性

一手：[Casaletti 2016](https://doi.org/10.1109/TAP.2016.2570251)、[arXiv:1703.01294](https://arxiv.org/pdf/1703.01294v1)、[Opt. Express 2015](https://doi.org/10.1364/OE.23.007593)、[Ansys Help Parametric](https://ansyshelp.ansys.com/public/views/secured/electronics/v251/en/subsystems/HFSS/Content/Optimetrics/SettingUpaParametricAnalysis.htm)、[ExportEigenmodes](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportEigenmodes.htm)、[Adding an Eigenmode Setup](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/AddinganEigenmodeSetup.htm)。

Oliner 与 Hessel 1959（IRE TAP 7(5), 201–208）与 Patel 与 Grbic 2011（IEEE TAP 59(6), 2087–2096）只核到题录与中文专利背景，连分式色散系数与辐射角公式标 **权威二手线索，待核验原文**。

确定性：HFSS 能力、官方限制、24 个 variation 的频率与带隙数值 **已核验**（本会话实测）；调制公式 **已核验**；带隙随 M 单调属 Oliner-Hessel 定性结论（题录级）；17 GHz 主模带隙、等效阻抗调制深度、漏波辐射角 **未知/未做**。
