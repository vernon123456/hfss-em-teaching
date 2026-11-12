# Slotted circular patch 单元与等效阻抗张量

## 结论

把方形 sliced patch 换成圆盘加穿心直槽，全部几何量做成 AEDT 设计变量，复用既有等效阻抗反解链路。**主轴角几乎精确跟随槽角**，端点偏差不超过 2.2°，明显优于方贴片 sliced patch 的 17 到 23° 偏差。8 单元超胞的带隙随调制深度打开，M=0.3 时约为方贴片基线的 2.6 倍。

## 术语核验

| 表述 | 映射 | 来源与状态 |
|---|---|---|
| 圆形开槽贴片单元（用户表述） | `slotted circular patch`、`circular patch with a slot` | [Fartookzadeh 与 Armaki, IEEE TAP 64(2), 826–830 (2016)](https://doi.org/10.1109/TAP.2015.2511152)、[IEEE IWS 2026](https://doi.org/10.1109/IWS69027.2026.11674610)，英文**已核验题录**；中文 `[术语未验证]` |
| 各向异性阻抗面 | `anisotropic impedance surface` | [Fong 2010](https://doi.org/10.1109/TAP.2010.2055812)、[Ansys Help](https://ansyshelp.ansys.com/public/views/secured/electronics/v251/en/subsystems/HFSS/Content/HFSS/AssigningAnisotropicImpedanceBoundaries.htm)，**已核验** |
| 等效表面电抗 | `effective surface reactance` | [Adv. Electron. Mater. 式(4)(5)](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aelm.70606)、[arXiv:2611.08166 式(28)](https://arxiv.org/html/2611.08166v1)，**已核验** |

## 模型

| 参数 | 值 |
|---|---|
| 单元 | p=3 mm，h=1.57 mm，εr=2.2，PEC 地板与顶盖 H=30 mm |
| 圆盘 | 半径 `patch_r`=1.2 mm，`create_circle` 接受表达式 |
| 槽 | 穿心矩形直槽，宽 `slot_w`（0.1/0.4 mm），角 `slot_ang`（0/45/90 deg），原生 `oEditor.Rotate` 变量表达式 |
| 周期边界 | 4 对 Lattice Pair，x 两对用 `phix`，y 两对用 `phiy` |
| 求解 | `HFSSEigen`，MinFreq 10 GHz，NumModes 12，MaxDeltaFreq 1% |
| Optimetrics | `SweepCircular` 扫 `slot_ang`（0/30/60/90 deg）与 `slot_w`（0.1/0.3/0.5 mm） |

圆盘与槽均为 2D sheet，用 PyAEDT `modeler.subtract` 切槽。60 个张量反解点沿 5 个传播方向、3 个相位幅度扫描；11 个 Optimetrics 新 variation 验证几何参数化。

## 张量结果

| 配置 | 主值 major/minor (Ω) | Xxy (Ω) |
|---|---|---|
| 槽角 0，w=0.4 | 153.0 / 132.0 | -0.65 |
| 槽角 45，w=0.4 | 159.0 / 126.9 | 16.04 |
| 槽角 90，w=0.4 | 150.7 / 131.4 | -0.21 |
| 槽角 0，w=0.1 | 154.2 / 139.9 | -0.54 |

| 槽角 (deg) | 拟合主轴角 (deg) | 残差 (Ω) |
|---|---|---|
| 0 | -1.78 | 0.41 |
| 45 | 45.42 | 0.64 |
| 90 | -89.36 | 0.26 |

90° 的 -89.36° 与 90° 模 180 等价。对照方贴片 sliced patch 的 23.26 / 46.04 / 72.62°，`tensor_fit.csv`，圆形开槽单元在端点的主轴控制更准。二次型拟合残差 0.26 到 0.64 Ω，本参数下近似成立。

## 超胞带隙对照

| M | 方贴片带隙 (GHz) | 圆形开槽带隙 (GHz) |
|---|---|---|
| 0.0 | 0.000965 | 0.001761 |
| 0.3 | 0.063781 | 0.163989 |

两组都在 phi=180° 区边界取最低两本征频率之差。M=0 时两者都基本闭合。**不能把 2.6 倍只归因于单元形状**：方贴片超胞调制的是 gap，圆形超胞调制的是圆盘半径，调制灵敏度不同。

## 失败样本与修正

| 现象 | 处理 |
|---|---|
| 首批 60 点 f1 全为 18.0014 | `ListVariations` 累积已求解 variation，`keys[0]` 是缓存结果。改空 variation key 导出当前 nominal 解；Optimetrics 导出改用求解前后 key 差集 |
| 前台超胞任务 SIGTERM | 改后台执行，12 点耗时 11m47s |
| 超胞只返回 3 个新 variation | 单独补 M=0、phi=180° 一点；M=0 的其余相位点与中间 M 未扫 |
| 退化校验非严格 | `slot_w`=0.1 mm 时 Xxy≈0 但 Xxx=154.2 与 Xyy=139.9 不等，槽仍保留方向性。未建无槽圆盘 |

## 限制

- 等效阻抗反解用二次型近似，严格关系见 Fong 2010 式(17)。
- **双谐振未显式观测**：Optimetrics sweep 的 f1 与 f2 间隔随槽宽变化平缓，本参数范围未出现明显双模靠近；加大 `slot_w` 或 `patch_r` 后可能改变，未验证。
- 超胞对照只有 M=0 与 M=0.3 的区边界点，中间 M 未扫；超胞里槽角固定 0°，调制的是圆盘半径。
- p=3 mm、λ0≈17.6 mm，p/λ0≈0.17 已超严格 λ/10，Fong 2010 的 17 GHz 单元同样如此。
- Eigenmode 禁辐射边界与频变材料（[Ansys Help](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/AddinganEigenmodeSetup.htm)），Driven 漏波分支未做；无实测对照。

## 复现

```
RUN_MODE=probe  python circular_patch.py   # 单点最小闭环
RUN_MODE=tensor python circular_patch.py   # 60 点反解与张量拟合
RUN_MODE=sweep  python circular_patch.py   # Optimetrics 几何扫描
RUN_MODE=post   python circular_patch.py   # 仅重算表与图
python circular_supercell.py               # 8 单元超胞带隙
```

解释器 `C:/Users/Verno/.workbuddy/binaries/python/envs/pyaedtmcp/Scripts/python.exe`，AEDT 2026.1 GUI 模式，脚本内注入 `ANSYSEM_ROOT261` 与 `AWP_ROOT261`。运行前清理残留 `.aedt.lock`。

## 文件清单

| 文件 | 用途 |
|---|---|
| `circular_patch.py` / `circular_supercell.py` | 单元与超胞脚本 |
| `tensor_patch.aedt`（运行时生成，未提交仓库）| 主工程，新增 design `circular` 与 `circular_supercell` |
| `circular_xeff.csv` / `circular_fit.csv` | 方向相关电抗与张量拟合 |
| `circular_sweep.csv` | 11 个 Optimetrics variation 的前 12 个模式频率 |
| `circular_supercell_results.csv` / `circular_bandgap_vs_M.csv` | 超胞结果与带隙对照 |
| `circular_xeff.png` / `circular_axis.png` / `circular_bandgap_vs_M.png` | 图表 |
| `circular.log` / `circular_supercell.log`（运行时生成，未提交仓库）/ `eig_circular*/`（`.eig` 未提交仓库）| 运行留痕与官方 `.eig` |

> 说明：`.aedt` / `.aedtresults/` / `eig*/` / `*.log` 等未提交仓库（见根目录 `.gitignore`），均由脚本运行时生成，可重建。

工程改动前曾在本地备份为 `.workbuddy/backups/tensor_patch/tensor_patch.aedt.20261109-4.bak`（**本地备份，未纳入仓库**）。`parametric`、`supercell` 与 `ideal_tensor.aedt` 未改动。

## 来源与确定性

一手：[Fartookzadeh 与 Armaki, IEEE TAP 64(2), 826–830 (2016)](https://doi.org/10.1109/TAP.2015.2511152)、[IEEE IWS 2026](https://doi.org/10.1109/IWS69027.2026.11674610)、[Fong 2010](https://doi.org/10.1109/TAP.2010.2055812)、[Ansys Help Parametric](https://ansyshelp.ansys.com/public/views/secured/electronics/v251/en/subsystems/HFSS/Content/Optimetrics/SettingUpaParametricAnalysis.htm)、[ExportEigenmodes](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportEigenmodes.htm)。

确定性：HFSS 能力、官方限制、60 点频率、张量拟合与带隙数值 **已核验**（本会话实测）；圆形开槽贴片的双频与张量结论 **已核验题录**；双谐振是否在该几何出现 **未知**（本参数未观测）；2.6 倍带隙差异的成因分解 **推断**。
