# Sliced-patch tensor impedance surface 与 HFSS Eigenmode 张量反解

## 结论

在实物方贴片单元上加斜切片，用 HFSS Eigenmode 沿 5 个传播方向反解 `effective normalized scalar impedance`，最小二乘拟合 2×2 阻抗张量。主轴角随切片角单调旋转（23.3° → 46.0° → 72.6°），独立闭环中拟合张量建理想各向异性边界后 5 个方向的 HFSS 频率与 17 GHz 目标最大偏差 **0.504%**。

两个必须记录的负面结果：论文参数 g_s=0.2 mm 在本案例基板（εr=2.2）上各向异性只有 1.03，接近拟合噪声；主轴角在 θ_s=0° 与 90° 两端分别偏差 +23.3° 与 −17.4°。

## 口径与修正（第 1 步核验）

| 项 | 开工前假设 | 核验后处理 |
|---|---|---|
| 数值对照 Fong Fig.8 的 384.2j/161.2j Ω | 可直接验收 | 该数值来自 1.27 mm Rogers 3010（εr=10.2）、10 GHz，与本案例 1.57 mm εr=2.2、17 GHz 不可比。改为趋势与自洽验证 |
| 反解方法 | 需自行推导 | [Fong 2010 式(17)](https://www.researchgate.net/publication/224151557_Scalar_and_Tensor_Holographic_Artificial_Impedance_Surfaces) 与 [US 7911407](https://freepatentsonline.com/7911407.html) 均写明 ≥3 个传播方向的波矢加最小二乘解 Zxx、Zxy、Zyy |
| 退化校验 | θ_s=0° 即无切片 | θ_s=0° 仍是水平切片。真正的标量退化是 **g_s=0**，已按此执行 |

## 术语核验

| 表述 | 映射 | 来源与状态 |
|---|---|---|
| 张量贴片单元 | `sliced-patch geometry`、`tensor impedance surface` | [Fong 2010 正文](https://www.researchgate.net/publication/224151557_Scalar_and_Tensor_Holographic_Artificial_Impedance_Surfaces)、[WO2017015308](https://patents.google.com/patent/WO2017015308A1/en)，英文**已核验**；中文 `[术语未验证]`，不作标题 |
| 等效标量阻抗 | `effective normalized scalar impedance`，随传播方向变化 | Fong 2010 式(17) 正文片段，权威二手转录 |
| 主轴与主值 | `principal axes`、阻抗张量特征值与特征向量 | [US 7911407](https://freepatentsonline.com/7911407.html)、[UCSD 学位论文](http://web.eng.ucsd.edu/ece/groups/electromagnetics/Theses/RyanQuarfoth.pdf)，**已核验** |

## 模型与反解

| 参数 | 值 |
|---|---|
| 单元 | p=3 mm，h=1.57 mm，εr=2.2，g=0.2 mm，PEC 地板，PEC 顶盖 H=30 mm |
| 切片 | g_s=0 / 0.2 / 1.0 mm，θ_s=0 / 45 / 60 / 90° |
| 周期边界 | 4 对 Lattice Pair，x 两对用 `phix`，y 两对用 `phiy` |
| 相位 | phix = k·cos θ_k，phiy = k·sin θ_k，θ_k=0/22.5/45/67.5/90° |
| 求解 | `HFSSEigen`，MinFreq 10 GHz，NumModes 8，MaxDeltaFreq 1% |

每个传播方向扫相位幅度 k，插值 f(k)=17 GHz 得 k*，β=k*(rad)/p，`X_eff = η0√((β/k0)²−1)`。拟合 `X_eff(θ) ≈ Xxx cos²θ + 2Xxy cosθ sinθ + Xyy sin²θ`，主轴角 `θ_p = ½·atan2(2Xxy, Xxx−Xyy)`，主值为 `A ± √(B²+C²)`。

二次型是**近似**。严格关系见 Fong 式(17)、[US 7911407](https://freepatentsonline.com/7911407.html) 与 [CLP 期刊式(3)](https://www.clppublishing.com/articles/OJ87af42b73853e7a7/html) 的非线性色散式。本案例 n=β/k0≈1.1，远离 [UCSD 论文](http://web.eng.ucsd.edu/ece/groups/electromagnetics/Theses/RyanQuarfoth.pdf) 指出的 n>5 椭圆失效区，拟合残差见下表。

共 121 个求解点。`eig_points.csv` 增量写入，中断可 resume；结果只走官方 [`ExportEigenmodes`](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportEigenmodes.htm)。

## 结果

退化校验：g_s=0、θ_k=0° 得 X_eff = **239.702 Ω**，上一案例 g=0.2 mm 的 239.816 Ω，差 0.05%。反解链路一致。

| θ_s (deg) | g_s (mm) | 主轴角 (deg) |
|---|---|---|
| 0 | 1.0 | 23.26 |
| 45 | 1.0 | 46.04 |
| 60 | 0.2 | 56.64 |
| 90 | 1.0 | 72.62 |

| 配置 | 主值 major/minor (Ω) | 残差 (Ω) |
|---|---|---|
| ts00_gs10 | 222.5 / 126.8 | 6.65 |
| ts45_gs10 | 202.4 / 145.3 | 3.07 |
| ts60_gs02 | 241.5 / 234.8 | 0.81 |
| ts90_gs10 | 220.1 / 144.1 | 8.34 |

`principal_angle.png` 显示主轴角单调随 θ_s 旋转，θ_s=45° 时几乎重合（46.0°），两端偏离。g_s=0.2 mm 配置主值比仅 1.03，切片耦合太弱；g_s=1.0 mm 提升到 1.39 到 1.75。

## 独立闭环

用 ts45_gs10 拟合的 Xxx=172.8、Xxy=28.5、Xyy=174.9 Ω 另建 `Anisotropic Impedance` 理想边界 HFSS 模型，按拟合张量预测的相位求解，检验 f 是否回到 17 GHz。

| θ_k (deg) | 理想 HFSS f (GHz) | 偏差 |
|---|---|---|
| 0 | 17.041 | +0.243% |
| 22.5 | 16.931 | -0.403% |
| 45 | 17.086 | +0.504% |
| 67.5 | 16.965 | -0.204% |
| 90 | 17.018 | +0.107% |

两个不同 HFSS 模型之间的吻合，避免了单点反解代回同公式的循环论证。

## 失败样本与修正

| 现象 | 处理 |
|---|---|
| g_s=0.2 mm 各向异性仅 1.03 | 三点探针确认 g_s=1.0 mm 把方向间频率差从 0.12 GHz 提到 0.43 GHz，随后按 1.0 mm 铺开 |
| 残留 `.aedt.lock` 使 resume 报 Project is locked | 脚本启动前自动清理同名锁并记录 |
| `.eig` 中 mode 1 频率与极小虚部粘成一列，tk=90° 被误读为 18.798 GHz（10.6% 假异常） | `parse_eig` 加正则回退，复用已落盘 `.eig` 重算，真实 17.018 GHz |
| 主轴角端点偏差 +23.3° 与 −17.4° | 未定位。候选为二次型近似在强各向异性下失效、Lattice Pair 的 U/V 方向、hybrid 模（**推断**） |
| 原生 `oEditor.Subtract` 在 gRPC 通道抛 `GrpcApiError` | 2D sheet 与 3D 薄 box 均试过，改用 PyAEDT 封装 `app.modeler.subtract` 后成功；旋转角改用原生 `oEditor.Rotate` 才接受变量 |

论文自己也报告 sliced gap 结构的两个主轴可达阻抗范围不重叠，无法同时满足式(23) 的两个主值，且仿真与近场测量需 1 到 1.37 标定，原因未知（[正文片段](https://www.researchgate.net/publication/224151557_Scalar_and_Tensor_Holographic_Artificial_Impedance_Surfaces)）。本案例只做单元表征，未复现 holographic 设计目标。

限制：纯仿真无实测；εr 取常数；全 PEC 无损；未勾 Save Fields 验场型与 hybrid 模；只扫 0 到 90° 传播方向；未做独立网格收敛研究；严格非线性反解未实现。

## 工程结构（2026-11-09 按物理模型拆分）

口径：物理模型不同的分开保存；同一模型只改参数的用 Optimetrics，不多建工程或 design。

| 工程 | design | 物理模型 |
|---|---|---|
| `tensor_patch.aedt` | `parametric` | 实物 sliced-patch 单元，θ_s/g_s/phix/phiy 全为 AEDT 变量，Optimetrics `SweepVars` 扫参数 |
| `ideal_tensor.aedt` | `ideal_tensor` | 理想 `Anisotropic Impedance` 边界闭环模型，独立物理模型 |

`tensor_patch.aedt` 内只剩 1 个 design。之前的 `patch_ts45_gs10` 与 `parametric` 是同一模型只改参数，已删除前者；`ideal_tensor` 物理模型不同，拆为独立工程。历史 121 点数据在 `eig_points.csv` 与 `eig/`，不依赖工程文件。

`tensor_patch.py` 保留为历史数据后处理脚本，只接受 `RUN_MODE=post`；仿真统一走 `parametric_scan.py`，闭环走 `ideal_tensor_check.py`（独立工程）。

改动前主工程已备份为 `.workbuddy/backups/tensor_patch/tensor_patch.aedt.20261109.bak`（158169 bytes，sha256 23aef5d0…）。早期 6 个配置工程与旧 `ideal_tensor.aedt` 备份在 `legacy_projects_20261108/`，均移入 Windows 回收站，可还原。

## Optimetrics 参数扫描（2026-11-09）

`parametric_scan.py` 在唯一工程内建 design `parametric`，切缝几何与相位全部由 AEDT 变量驱动。

| 变量 | 作用 | 本次取值 |
|---|---|---|
| `theta_s` | 切缝旋转角，原生 `oEditor.Rotate` 的 `RotateAngle` | 0/45/90 deg |
| `gs` | 切缝宽度，槽 sheet 尺寸 | 0.2/1 mm |
| `phix`, `phiy` | 两方向 Lattice Pair 相位 | 70 deg / 0 deg |

实现链：相对坐标系 `CS_center`（原点用 `p/2,p/2,hs` 表达式）→ 槽 sheet 绕 `CS_center` 按 `theta_s` 旋转 → `app.modeler.subtract("Patch","Slot")` 切缝 → 赋 PEC → Optimetrics Parametric setup `SweepVars` 同时扫 `theta_s` 与 `gs`。

6 个 variation 的 mode 1 频率（GHz）：

| theta_s / gs | 0.2 mm | 1.0 mm |
|---|---|---|
| 0 deg | 16.561 | 16.930 |
| 45 deg | 16.499 | 17.520 |
| 90 deg | 17.060 | 17.576 |

两个变量改值都引起频率明显变化，确认变量驱动几何。`ListVariations` 取回 6 个 variation key，逐个用 `ExportEigenmodes(solution, variation, path)` 导出 `.eig`，`export_parametric_results` 另导出 sweep 表。

已知限制：原生 `oEditor.Subtract` 在当前 gRPC 通道下抛 `GrpcApiError`，必须用 PyAEDT 封装 `modeler.subtract`；2D sheet 与 3D 薄 box 两种几何都测通布尔减，本案例用 2D sheet 以避免薄层网格。`phix`/`phiy` 未加入本次 sweep（会变成 6×7 个 variation），仍是设计变量，可加入同一 Parametric Setup。

## 复现

```
python parametric_scan.py                    # 实物单元主仿真，Optimetrics 扫 theta_s / gs
RUN_MODE=export python parametric_scan.py   # 只重导出 6 个 variation 结果
python ideal_tensor_check.py                # 独立工程 ideal_tensor.aedt，闭环验证
RUN_MODE=post python tensor_patch.py        # 历史 121 点数据重算表与图，不启动求解
```

解释器 `C:/Users/Verno/.workbuddy/binaries/python/envs/pyaedtmcp/Scripts/python.exe`，AEDT 2026.1 GUI 模式，脚本内注入 `ANSYSEM_ROOT261` 与 `AWP_ROOT261`。`tensor_patch.py` 在非 `post` 模式会主动报错，避免误建 design。

## 文件清单

| 文件 | 用途 |
|---|---|
| `tensor_patch.aedt` | 实物单元工程，单 design `parametric` |
| `ideal_tensor.aedt` | 理想边界闭环工程，单 design `ideal_tensor` |
| `parametric_scan.py` | 主仿真脚本，Optimetrics 参数扫描 |
| `tensor_patch.py` | 历史数据后处理，仅 `RUN_MODE=post` |
| `ideal_tensor_check.py` | 独立闭环脚本 |
| `parametric_results.csv` / `parametric_export.csv` / `eig_parametric/` | 6 个 variation 的本征频率与官方 `.eig` |
| `eig_points.csv` / `eig/` / `eig_ideal/` | 121 点原始本征频率与官方 `.eig` |
| `Xeff_by_angle.csv` / `tensor_fit.csv` | 方向相关等效电抗与张量拟合结果 |
| `tensor_patch.png` / `principal_angle.png` | X_eff(θ) 曲线、主轴角随切片角 |
| `ideal_tensor_compare.csv` / `.png` | 独立闭环数据与图 |
| `run.log` / `ideal_check.log` | 运行留痕 |

`scalar_impedance_eigenmode/` 与 `patch_unitcell/` 完全未改动，可作回滚基线。

## 来源与确定性

一手：[Fong 等, IEEE TAP 58(10), 3212–3221 (2010)](https://doi.org/10.1109/TAP.2010.2055812)、[US 7911407](https://freepatentsonline.com/7911407.html)、[CLP 期刊式(3)](https://www.clppublishing.com/articles/OJ87af42b73853e7a7/html)、[UCSD 学位论文](http://web.eng.ucsd.edu/ece/groups/electromagnetics/Theses/RyanQuarfoth.pdf)、[Ansys Help, Anisotropic Impedance](https://ansyshelp.ansys.com/public/views/secured/electronics/v251/en/subsystems/HFSS/Content/HFSS/AssigningAnisotropicImpedanceBoundaries.htm)、[Coupled Lattice Pair](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v261/en/Subsystems/HFSS/Content/HFSS/AssigningCoupledLatticePairBoundaries.htm)、[Adding an Eigenmode Setup](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/AddinganEigenmodeSetup.htm)。

IEEE Xplore 全文需订阅，ResearchGate 直接访问返回限制页。式(17)、Fig.8 数值与论文自报失败样本来自搜索引擎索引的正文片段（[链接](https://www.researchgate.net/publication/224151557_Scalar_and_Tensor_Holographic_Artificial_Impedance_Surfaces)），标 **权威二手转录，待核验原文**。

确定性：HFSS 能力、反解方法、本案例全部数值与闭环误差 **已核验**（官方文档或本会话实测）；二次型拟合 **推断**（近似）；主轴端点偏差根因 **推断**；论文自报失败样本 **已核验**（正文片段）。
