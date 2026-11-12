# Scalar impedance surface 最小案例与 HFSS Eigenmode 色散验证

## 结论

已跑完建模 → 边界 → HFSSEigen 求解设置 → 7 点相位扫描 → `.eig` 导出 → 解析验证 → 有耗对照的全流程。无损 `scalar impedance surface`（Rs=0, Xs=+200 Ω/□）上最低 TM 表面波模的 HFSS 本征频率与闭式解 **最大偏差 0.425%，平均绝对偏差 0.149%**。工程、脚本、原始数据、图表齐备，可重跑。

## 术语核验

| 表述 | 映射 | 来源与状态 |
|---|---|---|
| 标量阻抗面（用户表述） | `scalar impedance surface`，对应物理量 `surface impedance` Zs = Rs + jXs（Ω/square） | [Fong 等, IEEE TAP 58(10), 2010, 3212–3221](https://doi.org/10.1109/TAP.2010.2055812)、[Ansys Help: Impedance Boundaries](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Content/HFSS/ImpedanceBoundaries.htm)。**已核验** |
| 中文译名「标量阻抗面」 | 直译，未查到国标/IEEE 中文术语表依据 | `[术语未验证]`。本文不作标题定义，仅作文件名与口语指代；标准写作请用上表英文术语 |
| 本征仿真 | `Eigenmode solution`（本征模求解） | [Ansys Help: Eigenmode Solutions](https://ansyshelp.ansys.com/public/views/secured/electronics/v251/en/subsystems/HFSS/Content/HFSS/EigenmodeSolutions.htm)；谢拥军《HFSS原理与工程应用》书页 58。**已核验** |

Eigenmode 官方限制：禁端口/激励、禁辐射边界、禁扫频、禁看 S 矩阵；有耗结构给复频率与无载 Q（[Ansys Help: Eigenmode Data](https://ansyshelp.ansys.com/public/views/secured/electronics/v251/en/subsystems/HFSS/Content/ReportsandPostProc/ViewingEigenmodeSolutionData.htm)）。本案例的顶盖因此用 PEC，不用 Radiation。

## 模型与参数

- 空气盒 10 mm × 2 mm × 60 mm（变量 `p`/`w`/`H`），z=0 面为独立 sheet，赋 Impedance 边界 Rs=0、Xs=`Xs`=200 Ω/□。
- z=H 顶面 Perfect E；x 方向两对 Lattice Pair 相位取变量 `px`，y 方向固定 0°。用相位扫描替代扫频（Eigenmode 无扫频）。
- 求解类型 Eigenmode，`HFSSEigen`：MinimumFrequency 1 GHz，NumModes 4，MaxDeltaFreq 1%，MaximumPasses 12，MinimumPasses 3，MinimumConvergedPasses 2。
- 相位点 50°…170°，步长 20°，共 7 点；β = px(rad)/p，f 为各点最低本征模频率。
- 环境：AEDT 2026.1（v261）GUI 模式，PyAEDT 1.4.0，Windows。gRPC 端口随会话分配（本次出现 9998 / 4854 / 14169 / 13324）。

## 解析基准

无损、非调制的感性标量表面阻抗 Zs = jXs（Xs>0）支持 TM 表面波，色散关系

```
beta_sw = k0 * sqrt(1 + (Xs/eta0)^2)
alpha_z = k0 * Xs / eta0
```

两源交叉验证：[Casaletti 等 2016, 式 (2)](https://hal.sorbonne-universite.fr/hal-01342136v1/file/Casaletti2016.pdf)、[Sci Rep 2020, 式 (11)(12)](https://www.nature.com/articles/s41598-020-64278-9)。取 eta0 = 376.730313668 Ω，反解 f = c·beta/(2π·sqrt(1+(Xs/eta0)²))。H=60 mm 使 PEC 顶盖对束缚模的指数影响可忽略（最低频点 e^(-2·alpha·H) ≈ 0.007）。

## 结果

| px (deg) | f_HFSS mode1 (GHz) | 相对误差 (%) |
|---|---|---|
| 50 | 3.666638 | -0.300 |
| 70 | 5.146443 | -0.044 |
| 90 | 6.617081 | -0.041 |
| 110 | 8.106436 | +0.193 |
| 130 | 9.560914 | -0.011 |
| 150 | 11.036217 | +0.029 |
| 170 | 12.450899 | -0.425 |

完整数据（解析频率、β、mode 1–4、Q）见 `dispersion.csv`。解析与 HFSS 曲线见 `dispersion.png` / `dispersion.svg`。

误差两端偏大：50° 处频率低、场束缚弱，PEC 顶盖余量最小；170° 已接近布里渊区边界，周期边界的模式耦合更敏感。中间五点误差均 ≤0.193%。

## 有耗对照（复频率与无载 Q）

同模型、px=90°，仅把 Rs 从 0 改为 20 Ω/□，单独建 `scalar_impedance_lossy.aedt`：

| 条件 | mode 1 复频率 (GHz) | Q |
|---|---|---|
| Rs=0 | 6.617081 + j·O(1e-12) | 1.058e+12 |
| Rs=20 | 6.625575 + j·0.145660 | 22.7488 |

Q 从数值噪声级降到 22.75，复频率虚部升到 0.146 GHz，与官方「有耗本征模给复频率与无载 Q」一致。原始数据 `eig_90.eig`、`eig_lossy.eig`，汇总 `lossy_result.csv`。

## 失败样本与修正（不单向采信）

1. PyAEDT 1.4.0 的 `post.get_solution_data` 在 Eigenmode 下抛 `hfssconstants.default_solution` AttributeError；该轮 AEDT 会话随后退出，未保存工程与结果。改走官方原生 `Solutions.ExportEigenmodes`（[Ansys Help: ExportEigenmodes](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Subsystems/HFSS%20Scripting/Content/ExportEigenmodes.htm)），并让每个相位点求解后立即保存工程。
2. 原生 `ReportSetup.CreateReport` 试过三种报告类别/表达式组合，均未产出文件；弃用报告路径。
3. 独立 Python 进程不继承安装器变量，PyAEDT 报「AEDT is not installed」；脚本内注入 `ANSYSEM_ROOT261` / `AWP_ROOT261`。
4. 首版 `.eig` 解析按 tab 切分，把 Mode 序号 1/2/3/4 当成频率。按官方列格式（Mode | 复频率 GHz | Q）改为按空白切分取第 2 列，并新增 `RUN_MODE=post` 从已落盘 `.eig` 重算，避免重复求解。

## 限制

- Xs 为频率无关常数，是理想化模型；Fong 2010 的实物单元（3 mm 方贴片 / 1.57 mm εr=2.2 接地介质，17 GHz，Z 约 161j–234j Ω）具有色散，不在本案例内。
- 顶面 PEC 而非开放半空间；H 已按衰减长度取足，但低频端仍有可测残差。
- 纯仿真，无实测对照；未做网格收敛性独立研究，采用 MaxDeltaFreq 1% 与最少 3 次自适应 pass。
- 中文术语「标量阻抗面」标注 `[术语未验证]`，交付时需换成已核验英文术语。

## 复现

```
# 全流程（GUI 启动 AEDT，约 3–4 分钟）
C:/Users/Verno/.workbuddy/binaries/python/envs/pyaedtmcp/Scripts/python.exe build_and_run.py

# 仅用已有 .eig 重算 CSV/SVG/PNG（不启动 AEDT）
RUN_MODE=post  <python> build_and_run.py

# 有耗对照（Rs=20，单点）
RUN_MODE=lossy <python> build_and_run.py

# 复用已运行的 AEDT 会话（可选）
AEDT_REUSE_PORT=<port> AEDT_REUSE_PID=<pid> <python> build_and_run.py
```

## 文件清单

| 文件 | 用途 |
|---|---|
| `scalar_impedance_eigenmode.aedt`（运行时由 `build_and_run.py` 生成，未提交仓库）| 无损主工程；`.aedtresults/` 同样未提交 |
| `scalar_impedance_lossy.aedt`（运行时生成，未提交仓库）| 有耗对照工程 |
| `build_and_run.py` | 全流程可复现脚本 |
| `eig_*.eig` | 官方导出的本征模原始数据表 |
| `dispersion.csv` / `dispersion.png` / `dispersion.svg` | 色散数据与图 |
| `lossy_result.csv` | 有耗对照汇总 |
| `run.log` / `raw_reports.txt` / `solve.log`（运行时生成，未提交仓库）| 运行与失败样本留痕（过程产物） |

> 说明：`.aedt` / `.aedtresults/` / `*.log` 等二进制与求解产物未提交仓库（见根目录 `.gitignore`），均由 `build_and_run.py` 在运行时生成，删除后可重新跑出，无需纳入版本控制。
