# 六边形排列尝试记录（未完成，卡点已定位）

## 结论

菱形 WS 原胞与非正交 Primary/Secondary 边界的**最小闭环跑通**，但**核心物理验证未成立**，本轮结果不能用于判断六重对称性。17 GHz 附近色散贴近光锥，多数传播方向 β≤k0，等效阻抗反解公式不适用；Γ→M 扫描出现模式换序，按序号取 mode1 失效。计划 7 步中完成第 1、2 步与部分第 3、4 步数据，第 5 到 7 步未做。

## 术语核验

| 表述 | 映射 | 来源与状态 |
|---|---|---|
| 六边形排列（用户表述） | `hexagonal lattice`、`triangular lattice`、`C6v symmetry` | [IEEE TAP, Dispersion Analysis of Metasurfaces With Hexagonal Lattices With Higher Symmetries](https://ieeexplore.ieee.org/document/10256254/)、[Ding 与 He, Opt. Express 25, 20757 (2017)](https://doi.org/10.1364/OE.25.020757)，英文**已核验**；中文 `[术语未验证]` |
| 不可约布里渊区 | `irreducible Brillouin zone`，Γ-M-K-Γ | [IEEE 论文附录 A](https://www.researchgate.net/publication/374064938_Dispersion_Analysis_of_Metasurfaces_With_Hexagonal_Lattices_With_Higher_Symmetries)、[ScienceDirect 专著章节](https://sciencedirect.com/book/9780128205969)，**已核验** |
| 周期边界对 | `Primary`/`Secondary` boundary, U/V vectors | [Ansys Help, Coupled Lattice Pair](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v261/en/Subsystems/HFSS/Content/HFSS/AssigningCoupledLatticePairBoundaries.htm)，**已核验** |

## 已完成

| 项 | 结果 |
|---|---|
| 菱形原胞 | a1=a(1,0)、a2=a(1/2,√3/2)，a=3 mm；`create_polyline` 加 `sweep_along_vector` 建 Substrate 与 Air |
| 单元 | 圆盘 `disc_r` 从 1.117 mm 调到 1.28 mm（菱形内切圆 1.299 mm 是上限） |
| 边界 | 4 对显式 U 向量的 Primary/Secondary，两方向相位 `phi1`=k·a1、`phi2`=k·a2 |
| 验证 | `validate_simple`=True，Γ 点单点 20.6 s 出 12 个模式 |
| 数据 | 5 方向 × 3 幅度共 15 点 f(β)；Γ→M 段 7 点色散 |

Γ→M 段按 M=(π,0) 即 `phi1` 0→180 deg、`phi2`=0 扫描，与 [IEEE 论文式(11)-(14)](https://ieeexplore.ieee.org/document/10256254/) 的 Γ→M 条件一致。

## 三个卡点

| 现象 | 状态 |
|---|---|
| 变量名 `R` 导致 `create_circle` 连续失败 | 定点诊断确认单字母变量名冲突（同类坑：`g0`），改名 `disc_r` 后解决。**已解决** |
| 17 GHz 反解出 β≤k0，`sqrt` 报 domain error | 把圆盘半径从 1.117 增到 1.28 mm 后，θ=0/22.5/45 仍无束缚表面波，仅 θ=67.5 给出 Xeff=74.67 Ω。**物理障碍，未解决** |
| Γ→M 的 f1 不连续：13.91 → 10.37 → 17.48 GHz | **已定位**，`MinimumFrequency=10GHz` 截断低频分支，见下方诊断结果。前述 V 向量假设已排除 |

15 点数据里 f1 减光锥频率从 +0.33 到 -2.14 GHz，色散曲线穿越光锥，说明该几何在 17 GHz 附近处于慢波与快波边界。θ=0 与 θ=90 在相同 β 下 f1 相差约 0.85 GHz，与 C6v 各向同性预期不符；更可能是边界相位符号或模式识别问题，**不能据此下物理结论**。

## 未完成

- 六重对称张量验证（Xxy≈0、Xxx≈Xyy）
- 完整 Γ-M-K-Γ 色散与 K 点简并判定
- 加单向槽量化 C6v 破缺
- 8 单元超胞带隙对照
- 菱形原胞与矩形超胞交叉验证

## 诊断结果（2026-11-09 晚，修正前述假设）

`dev_history/hexagonal_diagnose.py` 做了两件事：相位对称性检验，以及低相位段分支追踪。频率连续性用来替代场型图，原因是 Eigenmode 场量导出路径在本工作区前几轮已验证不可靠（`post.get_solution_data` 崩、`CreateReport` 无输出）。

| 检验 | 结果 |
|---|---|
| 对称性 | `phi1=90, phi2=0` 与 `phi1=0, phi2=90` 的 f1 为 19.8117 与 19.8722 GHz，差 0.0606 GHz；60 deg 组差 0.1388 GHz。mode2/mode3 也几乎重合 |
| V 向量假设 | **排除**。两对 Primary/Secondary 的相位方向与 U/V 设置基本正确，`validate_simple`=True 之外拿到了独立对称性证据 |
| 低相位分支 | `phi1`=25/30/35 复算得 f1 = 15.560 / 10.368 / 11.700 GHz，30 deg 点可复现且 35 deg 落在同一低分支上 |

决定性验证：新建 `Eigen1_Low` setup，`MinimumFrequency=5GHz`、`NumModes=8`，重跑 `phi1`=20/25/30。

| phi1 (deg) | 5 GHz setup 前 6 模 (GHz) |
|---|---|
| 20 | 7.812, 8.070, 14.992, 15.987, 20.114, 24.456 |
| 25 | 9.068, 9.392, 15.549, 16.679, 20.317, 24.763 |
| 30 | 10.363, 10.790, 16.169, 17.488, 20.748, 25.232 |

存在一条随相位单调上升的低频分支，`phi1`<30 时低于 10 GHz 被原 setup 排除，`phi1`=30 时越过 10 GHz 进入求解窗口并占据 mode1/mode2，把原表面波分支挤到 mode3。原 setup 在 `phi1`<30 时 reported 的 mode1（15.0/15.6 GHz）实际是第 3 个模式。**10.37 GHz 跳变是求解下限造成的人为假象，不是物理带隙或模式换序。**

推论：之前 15 点反解用的 f1 混了两个不同分支，得到的 Xeff 与 β≤k0 判断需要用 5 GHz 下限重跑并按频率连续性追踪分支后复核。

## 5 GHz 下限重跑（2026-11-10，已完成）

`hexagonal_patch.py` 改用 `Eigen1_Low`（MinFreq=5 GHz、NumModes=8），重跑 5 方向 × 3 幅度共 15 点，每点记录前 8 个模式，并按「锚定 amp=70 时最接近 17 GHz 的模式，再向 60/80 取最近频率」做分支追踪。

| 现象 | 结果 |
|---|---|
| 数据 | 15 点全部出数，无报错。所有方向在追踪到的分支上都报 `no 17GHz crossing` |
| 分支追踪 | nearest 法在 theta=0 把 amp=60 误配到 mode2（17.31 GHz），而正确分支应为 mode1（16.69 GHz）。3 点 nearest 不足以稳健追踪 |
| 复核 | 直接按各方向 mode1 分支插值到 17 GHz，见下表 |

| theta (deg) | amp* (deg) | beta (rad/m) | beta/k0 | Xeff (Ω) |
|---|---|---|---|---|
| 0 | 61.67 | 358.8 | 1.0070 | 44.6 |
| 22.5 | 60.04 | 349.3 | 0.9804 | 无解 |
| 45 | 60.30 | 350.8 | 0.9846 | 无解 |
| 67.5 | 62.44 | 363.3 | 1.0196 | 75.0 |
| 90 | 67.61 | 393.4 | 1.1040 | 176.2 |

k0=356.29 rad/m。**β/k0 从 0.98 跨到 1.10，Xeff 从无解跳到 176 Ω**，与 C6v 各向同性矛盾。这确认 17 GHz 处不存在统一的束缚表面波分支，反解公式 `Xs=η0√((β/k0)²−1)` 不适用。上一轮悬置的「17 GHz 贴近光锥是否仍成立」现在标**已核实成立**；卡点从技术设置转为物理与工作点选择。

晶格设置本身已由上一轮的对称性检验证实（两个等价方向 f1 差 0.0606 / 0.1388 GHz），无需依赖张量反解。

## 建议的下一步

换工作点，不要继续调求解设置。把目标频率移到色散明显低于光锥的区间，或改几何提高等效电抗（例如换用方贴片或缩小单元周期），再重做 5 方向反解。更稳妥的替代是直接用对称性检验与色散曲线表征六边形晶格，绕开 17 GHz 的阻抗反解。

## 六边形 WS 原胞替换尝试（2026-11-10 晚，未成功，已回滚）

按「采用六边形超晶胞替换菱形原胞」把 `hexagonal` design 换成正六边形 Wigner-Seitz 原胞。建模与 `validate_simple` 通过，Eigenmode 求解持续失败，工程已回滚。

| 项 | 值 |
|---|---|
| 几何 | 正六边形，内切圆 1.5 mm（菱形为 1.299 mm），圆盘 `disc_r`=1.35 mm |
| 边界 | 3 组对边 × 2 层 = 6 对 Primary/Secondary，共 15 个边界 |
| 相位 | `phi_v`=phi1、`phi_u`=phi2、`phi_w`=phi2−phi1 |

| 检查 | 结果 |
|---|---|
| 几何与变量 | Substrate / Air / Disc 齐全，7 个变量全部注册，`validate_simple`=True |
| 求解 | `Eigen1`、`Eigen1_Low`、新建 `Eigen1_WS` 都 `analyze_setup` 返回 False、`is_solved`=False、约 5 s |
| 相位表达式 | `phi_w` 改成字面 `0deg` 后仍失败，排除表达式引用问题 |
| 隔离实验 | `DeleteBoundary` 在当前 gRPC 通道抛 `GrpcApiError`，`GetBoundaryProps` 同样不可用，无法删除第三组边界验证 |
| 对照 | 菱形原胞 4 对边界可正常求解 |

可能原因（未验证）：三组非正交周期边界过度约束（六边形晶格只有 2 个独立晶格矢量）；某组配对面的 U/V 向量方向不匹配。`validate_simple` 不检查这两项。

回滚路径：当前尝试状态备份为 `.workbuddy/backups/tensor_patch/tensor_patch.aedt.20261110-ws_attempt.bak`；工程已还原到 `tensor_patch.aedt.20261110-3.bak`（菱形，可求解）。`dev_history/hexagonal_ws.py` 保留供后续调试，它会重建六边形几何，运行前须先备份。

诊断问题：三组周期边界中哪一组让求解器拒绝。需要在 AEDT GUI 或用原生 COM 命令逐组删除验证。

## 矩形超胞替换（2026-11-10 晚，已成功）

按用户选定的「改矩形超胞保持正交边界」替换 `hexagonal` design。六边形 WS 原胞的三组非正交边界在本环境求解失败，矩形超胞复用已验证可求解的 4 对正交 Lattice Pair。

| 项 | 值 |
|---|---|
| 超胞 | Lx=a=3 mm，Ly=√3a=5.196 mm，含 2 个格点 |
| 单元 | 中心 1 个完整圆盘（R=1.2 mm）加四角各 1 个 1/4 圆扇形片，14 段折线近似 |
| 边界 | 4 对 `assign_lattice_pair`，x 两对 `phi_x`、y 两对 `phi_y`；PEC 地板与顶盖 |
| 求解 | `Eigen1_Rect`，MinFreq 5 GHz，NumModes 8 |

| 验证 | 结果 |
|---|---|
| 最小闭环 | 7 对象、7 边界、`validate_simple`=True，Γ 点 20.7 s 出数 |
| Γ 点简并 | f1/f2=9.377948/9.378810 GHz，f3/f4=13.771760/13.775767 GHz，两对近简并 |
| 色散 | `phi_y` 0/30/60/90/120/150/180 deg 共 7 点全部出数 |

f1 从 9.378 GHz 降到 6.642 GHz（30 deg）再升到 24.083 GHz（180 deg）。低频分支在 5 GHz 下限内被捕获，30 deg 处的下降是矩形超胞能带折叠，未再出现 10 GHz 截断造成的假跳变。

限制：矩形超胞布里渊区只有原胞的一半，模式数翻倍；`phi_x`/`phi_y` 到三角晶格 Γ-M-K 高对称点的映射需按 [IEEE document 10980079](https://ieeexplore.ieee.org/document/10980079/) 重算，本轮只扫了 `phi_x`=0 的 `phi_y` 段。四角扇形片为折线近似。17 GHz 阻抗反解未重做，上一轮「该工作点无统一束缚表面波」的结论继续适用。

文件：`hexagonal_rect.py`、`hexagonal_rect_dispersion.csv`、`hexagonal_rect_dispersion.png`、`hexagonal_rect.log`、`eig_hexagonal_rect/`。改动前工程备份为 `tensor_patch.aedt.20261110-4.bak`。

## Γ-M-K-Γ 两段相位扫描（2026-11-10，已完成）

依据 [IEEE TAP document 10980079 全文](https://www.scieee.com/paper/243108230/text)：矩形超胞 `px=a`、`py=√3a` 下，Γ→M 用 `phi_x=0` 固定、扫 `phi_y`；M→K 与 K→Γ 可由 `phi_y=0` 的 Γ→K1 路径配合 Appendix B 后处理重折叠得到；超胞 BZ 在 y 方向减半，原胞一模对应两解。

| 项 | 值 |
|---|---|
| setup | `Eigen1_IBZ`，MinFreq 5 GHz，NumModes 12 |
| Γ→M | `phi_x`=0，`phi_y` 0/30/60/90/120/150/180 deg |
| Γ→K1 | `phi_y`=0，`phi_x` 0/30/60/90/120/150/180 deg |
| 实现 | 脚本循环改变量加空 variation key 导出 |

第 2 步原计划用 Optimetrics 两个单变量 sweep，实际改用脚本循环。原因是两段各只需改一个变量，脚本循环可避开 Optimetrics 累积 variation 与 `ListVariations` 差集导出的已知坑，且 `hexagonal_rect.py` 同一路径已验证可靠。

| phi_y (deg) | Γ→M f1 (GHz) | phi_x (deg) | Γ→K1 f1 (GHz) |
|---|---|---|---|
| 0 | 9.371 | 0 | 9.371 |
| 30 | 6.643 | 30 | 8.163 |
| 60 | 9.397 | 60 | 15.616 |
| 90 | 13.762 | 90 | 21.502 |
| 120 | 17.543 | 120 | 26.806 |
| 150 | 20.941 | 150 | 31.783 |
| 180 | 24.079 | 180 | 36.457 |

两段 Γ 点前 4 模完全一致（9.371189 / 9.374031 / 13.740401 / 13.753793 GHz），构成独立交叉校验。Γ→M 段与上一轮 `hexagonal_rect_dispersion.csv` 的 7 点逐点对齐，最大差约 0.05 GHz，差异来自 NumModes 8 改 12 与网格重划分。

简并对共 14 组（相邻模频差小于 0.02 GHz）。Γ 点有 3 组，最小 gap 0.002842 GHz。

**K 点检查**：由倒格矢推导（非论文原表），超胞 BZ 的 k_x 范围为 ±π/a，原胞 K=(4π/(3a),0) 平移 −2π/a 后折到 k_x=−2π/(3a)，对应 `phi_x`=−120 deg，与 +120 deg 由时间反演等价。该点最低分支最小相邻间隔 0.269819 GHz，**未观察到 Dirac 锥式简并**。`phi_x`=180 deg 处高模 7/8 与 9/10 有简并（gap 0.006989 / 0.003892 GHz），但不属于最低分支。

未完成：严格 Appendix B 重折叠未做（未取得该附录全文），因此没有给出物理上完整的 Γ-M-K-Γ 拼接曲线。交付图 `hexagonal_ibz_dispersion.png` 是两段原始相位扫描，横轴为各自相位，不做误导性拼接。

限制：纯 Lattice Pair 相位扫描可能只覆盖偶模，论文用 M/E 对称面组合区分奇偶模；四角扇形片为 14 段折线近似，可能人为劈裂简并；17 GHz 阻抗反解未重做，上一轮「该工作点无统一束缚表面波」结论继续适用。

文件：`hexagonal_ibz.py`、`hexagonal_ibz.csv`、`hexagonal_ibz_degeneracy.csv`、`hexagonal_ibz_dispersion.png`、`hexagonal_ibz.log`、`eig_hexagonal_ibz/`。改动前工程备份为 `tensor_patch.aedt.20261110-6.bak`。

确定性：两段 14 点频率、Γ 点交叉校验、14 组简并对、K 候选点无最低分支简并 **已核验**（本会话实测）；相位条件与超胞尺寸 **已核验**（IEEE 论文原文）；K 点折叠位置 **推导**（基于倒格矢，非论文原表）；严格重折叠与 Dirac 锥结论 **未知**。

## 按论文原文的 Table IV、Appendix B 与对称面重做（2026-11-11 凌晨）

用户提供全文 PDF（`A_Symmetry-Based_Multimodal_Transfer-Matrix_Method_for_the_Analysis_of_2D-Periodic_Structures.pdf`）。**期刊修正**：该文为 [Jimenez-Suarez 等, IEEE Trans. Microw. Theory Techn., 73(9), 6242–6244 (2025)](https://ieeexplore.ieee.org/document/10980079/)，此前记录误标为 IEEE TAP，已更正。

### 术语核验

| 表述 | 映射 | 来源与状态 |
|---|---|---|
| 重折叠（用户表述） | `fold` / `postprocessing to rebuild the dispersion diagram` | PDF Appendix B 原文，英文**已核验**；中文 `[术语未验证]` |
| 对称面组合 | `M` = PMC (`n̂·E=0`)，`E` = PEC (`n̂×E=0`)；`M^ν_0 M^ν_{p_ν/2}`、`E^ν_0 E^ν_{p_ν/2}` | PDF Table VI、Fig. 15、Appendix A，**已核验** |
| 奇偶模 | `even/odd modes`，对应 `2nπ / (2n+1)π` 相位 | PDF Section IV-A，**已核验** |

### 原文规则与修正

| 项 | 上一轮 | Table IV / Appendix B 原文 |
|---|---|---|
| ΓM 段 | `φy` 0→π | SC `Δφy`=[0, 2π]，须扫到 360° |
| ΓK1 段 | `φx` 0→π | SC `Δφx`=[0, 4π/3]，须扫到 240° |
| 分支分配 | 未做 | 基模由 `0≤φx≤π` 与 `π≤φx≤4π/3`（第一 BZ 折回 `2π−φx∈[2π/3,π]`）两支拼接，对应 PC 路径 ΓK；`0≤φx≤2π/3` 的后向模对应 PC 路径 KM |

### 执行结果

| 项 | 结果 |
|---|---|
| 扩展扫描 | `dev_history/hexagonal_ibz_full.py`，ΓM 13 点（0…360°）加 ΓK1 9 点（0…240°），共 22 点全部出数 |
| 数据自洽 | ΓM 段 `φy` 与 `360−φy` 频率完全一致（30°/330° 均 6.6426 GHz）；ΓK1 段 `φx` 与 `360−φx` 一致（150°/210° 均 31.783 GHz） |
| 奇偶模 | `dev_history/hexagonal_sym.py` 建半超胞（Ly/2），y=0 与 y=Ly/2 加对称面。偶模双 PMC（`M^y_0 M^y_{p_y/2}`），奇模双 PEC（`E^y_0 E^y_{p_y/2}`），各 9 点全部出数 |
| Γ 点分解 | 全超胞近简并对 9.371189/9.374031 GHz 分解为 even 9.380732 与 odd 9.368432 GHz |
| 图 | `hexagonal_GMK_path.png`，四段高对称点标注，含 5 组曲线与奇偶模散点 |

### 未达到可发表标准（必读）

图在 M 与 K 处相邻段分支**不衔接**：Γ-M 终点 24.08 GHz，M-K 起点 26.81 GHz；K-Γ 起点 36.46 GHz。分支分配仍是按频率连续性的启发式，没有严格复现 Appendix B 的本征解分类。

原因：论文用 MMTMM 加对称面组合把 2D 周期问题降为 1D 本征问题，能区分 even/odd 本征模并计算复波数模；Appendix B 明确写出绿色复模态「HFSS ES does not find this mode because its wavenumber is a complex number」。本工作区只有 HFSS Eigenmode 实频 `.eig` 输出，无法识别该分支，也无法按本征解给 `ΓK1` 的各支贴 MK 或 KΓ 标签。论文算例是六边形孔光子晶体，本案例是圆盘贴片加 PEC 盖，几何与模式族也不同。

因此 `hexagonal_GMK_path.png` 只能作为**分段扫描与折叠规则的示意图**，不能作为可发表的完整 Γ-M-K-Γ 色散图。要达到可发表，需要实现 MMTMM 本征求解或取得各模式的场型/复波数分类，再按 Appendix B 分配分支。

文件：`dev_history/hexagonal_ibz_full.py`、`hexagonal_ibz_full.csv`、`hexagonal_ibz_folded.csv`、`hexagonal_ibz_path.png`、`dev_history/hexagonal_sym.py`、`hexagonal_sym_even/odd.csv`（奇模 CSV 由 `hexagonal_sym_odd.csv` 给出）、`hexagonal_sym_modes.csv`、`hexagonal_GMK_path.csv/png`、`dev_history/hexagonal_gmk.py`、各 `*.log` 与 `eig_*` 目录。改动前工程备份 `tensor_patch.aedt.20261110-8.bak`。

确定性：Table IV 范围、Appendix B 分支规则、Table VI 对称面组合 **已核验**（用户提供的 PDF 原文）；22 点频率、`φ↔2π−φ` 对称性、奇偶模各 9 点频率、Γ 点分解 **已核验**（本会话实测）；分支到 MK/KΓ 的分配 **启发式推断**；可发表性 **未达成**。

## x 方向对称面分离（2026-11-11，已完成）

按用户选定路径，补 ΓM 段的 x 方向 parity 分解。新建半超胞 x∈[0, px/2]、y∈[0, py]，x=0 与 x=px/2 加对称面，y 方向保留 2 对 Lattice Pair 扫 `phi_y`。偶模 `M^x_0 M^x_{p_x/2}`（双 PMC），奇模 `E^x_0 E^x_{p_x/2}`（双 PEC），各 13 点（0 到 360 deg）。

| 步 | 结果 |
|---|---|
| 几何闭环 | 7 对象、7 边界、`validate_simple`=True |
| Γ 点校验 | 半超胞 9.353546 GHz 对全超胞 9.371189 GHz，偏差 0.018 GHz（0.19%），几何等价性通过 |
| parity 分解 | Γ 点全超胞近简并对 9.371189/9.374031 GHz 分解为 x_even 9.353546 与 x_odd 9.371219 GHz；`phi_y`=180 处全超胞 24.079/26.780 GHz 分别落在偶奇两支 |
| 对称性 | 两组谱各自满足 `φy` 与 `360−φy` 频率一致 |

### M、K 处真实拼接残差

第一版残差指标误算成同一相位两条 parity 分支的间距，已修正为「相邻路径段在接点处的频率差」。

| 接点 | 残差 (GHz) |
|---|---|
| M even，`phi_y`=180 对 `phi_x`=120 | 2.109695 |
| M odd，`phi_y`=180 对 `phi_x`=120 | **0.000572** |
| M even 备选，`phi_y`=360 | 0.906954 |
| K even，`phi_x`=0 对 `phi_x`=180 | 5.812544 |
| K odd，`phi_x`=0 对 `phi_x`=180 | 4.498975 |
| K even 备选，`phi_x`=0 对 `phi_x`=120 | **0.714387** |
| K odd 备选，`phi_x`=0 对 `phi_x`=120 | 1.381020 |

对照上一轮启发式图，M 处约 2.73 GHz、K 处约 28.5 GHz。奇偶分离后 M 的 odd 分支几乎精确闭合，K 的最优配对降到 0.71 GHz。

**仍未完全闭合**。even 分支在 M 处仍有 0.91 到 2.11 GHz，K 处仍有 0.71 到 1.38 GHz。可能原因：只用了 `M·M` 与 `E·E` 两组，Fig. 15 的混合组合 `E^x_0 M^x_{p_x/2}`、`M^x_0 E^x_{p_x/2}` 对应 `φx=π` 尚未计算；Appendix B 的复模态 HFSS ES 仍拿不到。分支到路径的分配依旧是启发式。

`hexagonal_GMK_parity.png` 是 parity 标记后的分段扫描图，M、K 处仍可见跳变，不能作为可发表的完整 Γ-M-K-Γ 色散图。

文件：`dev_history/hexagonal_symx.py`、`hexagonal_symx_even.csv`、`hexagonal_symx_odd.csv`、`hexagonal_parity_modes.csv`、`hexagonal_parity_residual.csv`、`hexagonal_GMK_parity.png`、`dev_history/hexagonal_gmk_v2.py`、`hexagonal_symx.log`、`eig_hexagonal_symx/`。工程新增 design `hexagonal_sym_x` 与 `hexagonal_sym_x_odd`，改动前备份 `tensor_patch.aedt.20261111-2.bak`。

确定性：26 点频率、Γ 点校验、parity 分解、残差数值 **已核验**（本会话实测）；Table VI 组合 **已核验**（PDF 原文）；残差指标定义 **已修正**；even 分支未闭合的成因 **推断**；可发表性 **未达成**。

## 混合对称面组合（2026-11-11，已完成）

按用户选定路径补齐 [Fig. 15(c)(d)](https://ieeexplore.ieee.org/document/10980079/) 的 `E^x_0 M^x_{p_x/2}`（em）与 `M^x_0 E^x_{p_x/2}`（me）。`dev_history/hexagonal_symx.py` 加 `SYMX_MODE`，`set_symmetry` 改为两个面独立 `is_perfect_e`，边界名带 mode 后缀。两组各 13 点（`phi_y` 0 到 360 deg）全部出数。

**验收口径修正**：混合组合固定 `φx=π`，其 `phi_y`=0 不该比全超胞 Γ 点 9.371189 GHz，应比 `phi_x`=180 的 36.456812 GHz。实测 em 36.563750、me 36.551101 GHz，偏差 0.09 到 0.11 GHz，几何与相位对应成立。

| x 方向组合 | 相位条件 | `phi_y`=0 的 f1 (GHz) |
|---|---|---|
| `M·M`（mm） | `φx=0` | 9.353546 |
| `E·E`（ee） | `φx=2π` | 9.371219 |
| `E·M`（em） | `φx=π` | 36.563750 |
| `M·E`（me） | `φx=π` | 36.551101 |

### 六组谱的 M、K 残差

| 接点 | 残差 (GHz) |
|---|---|
| M 全局最优 `ee@180` 对 `y_odd@120` | 0.000572 |
| M `mm@180` 对 `y_even@120`（上一轮 even 卡点） | 2.109695 |
| M `em@180` 对 `y_even` | **0.113119** |
| M `me@180` 对 `y_odd` | **0.060107** |
| M `em@180` 对 `y_odd` | 0.166708 |
| K 全局最优 `y_even@0` 对 `y_even@120` | 0.714387 |

混合组合把 even 分支在 M 处的候选配对从此前 0.907 到 2.110 GHz 压到 0.113 GHz，K 点未改善。

### 辩证核查（必读）

新配对位于 39 GHz 高频段，且跨越 `φx=0` 与 `φx=π` 两个相位切片。频率数值接近**可能只是巧合**，是否属于同一个 M 点须按论文 Fig. 13(d) 的 SC/PC 布里渊区映射判定，本轮没有做该判定。因此不能写成「even 分支已闭合」。K 点 0.714387 GHz 的断点仍在，分支到路径的分配依旧是启发式，[Appendix B](https://ieeexplore.ieee.org/document/10980079/) 的复模态 HFSS ES 仍拿不到。

`hexagonal_GMK_six.png` 是六组 parity/相位条件谱的分段扫描图，仍不能作为可发表的完整 Γ-M-K-Γ 色散图。

文件：`dev_history/hexagonal_symx.py`（改 `SYMX_MODE`）、`hexagonal_symx_em.csv`、`hexagonal_symx_me.csv`、`hexagonal_sixspectra_modes.csv`、`hexagonal_sixspectra_residual.csv`、`hexagonal_GMK_six.png`、`dev_history/hexagonal_gmk_v3.py`、`eig_hexagonal_symx/`。工程新增 design `hexagonal_sym_x_em` 与 `hexagonal_sym_x_me`，改动前备份 `tensor_patch.aedt.20261111-4.bak` 与 `dev_history/hexagonal_symx.py.20261111-2.bak`。

确定性：26 点频率、Γ 点校验、六组谱汇总、残差数值 **已核验**（本会话实测）；Fig. 15 混合组合 **已核验**（PDF 原文）；`φx=π` 由 y 方向类推 **推导**；39 GHz 配对是否为物理闭合 **未知**；可发表性 **未达成**。

## k 矢量核对（2026-11-11 晚，已完成，结论修正）

纯解析核对，无新仿真。目标是把「频率接近」与「物理闭合」区分开。

### 映射与判据

| 项 | 取值 |
|---|---|
| 超胞 | `px=a=3 mm`、`py=√3a`；SC 倒格矢 `B1=(2π/a,0)`、`B2=(0,2π/(√3a))` |
| 原胞 | 三角晶格倒格矢 `b1=(2π/a, −2π/(√3a))`、`b2=(0, 4π/(√3a))` |
| 高对称点 | `M0=(0, 2π/(√3a))`、`K0=(4π/(3a), 0)`，各按 60° 旋转取等价点集（[术语未验证]，英文 `star of M/K`） |
| 相位到 k | x 方向谱的 `φx` 由对称面固定（`mm`=0、`ee`=2π、`em/me`=π），`k_y=φy/py`；y 方向谱的 `φy` 固定（`y_even`=0、`y_odd`=2π），`k_x=φx/px` |
| 闭合判据 | 两侧 k 之差或之和须等于 `m·b1+n·b2`（整数 m,n），且两侧同落目标高对称点 |

### 结果

`dev_history/hexagonal_kcheck.py` 逐个核对残差表的 10 个候选配对。**全部 `same_k_mod_lattice=False`，全部判定为 FREQUENCY COINCIDENCE ONLY**。

| 配对 | 频差 (GHz) | kA | kB | 高对称点归属 |
|---|---|---|---|---|
| `ee@180` 对 `y_odd@120` | 0.000572 | (2.0944, 0.6046) | (0.6981, 1.2092) | A 不在 M，B 落在 K 等价点 |
| `em@180` 对 `y_even@120` | 0.113119 | (1.0472, 0.6046) | (0.6981, 0) | A 落在 M 等价点，B 落在 K 等价点 |
| `me@180` 对 `y_odd@120` | 0.060107 | (1.0472, 0.6046) | (0.6981, 1.2092) | A 落在 M 等价点，B 落在 K 等价点 |
| `mm@360` 对 `y_even@120` | 0.906954 | (0, 1.2092) | (0.6981, 0) | A 等于 `M0`，B 落在 K 等价点 |

39 GHz 的 `em/me@180` 一侧确实落在 M 等价点，但 y 方向谱在 `φx=120` 落在 K 等价点。M 对 K，频率接近属巧合。`mm@360` 的 kA 恰为 `M0`，印证 SC 的 `φy=2π` 折回原胞 M 点，也解释了 `φy` 与 `2π−φy` 频率相同。

### 即时修正先前结论

此前记录写的「M odd 闭合到 0.000572 GHz」「混合组合把 even 候选压到 0.113 GHz」都只是**频率数值接近**，k 矢量模倒格矢不等价，物理闭合**零例**。残差数值下降成立，物理闭合从未成立。相关段落与 `hexagonal_GMK_*.png` 的定性表述一并以此节为准。

可发表性结论不变且更强：分支到路径的分配缺少 k 矢量判据，Appendix B 的复模态 HFSS ES 仍拿不到，[Fig. 13(d)](https://ieeexplore.ieee.org/document/10980079/) 的 SC/PC 映射显示当前候选配对跨 M 与 K 两个不同高对称点。

文件：`dev_history/hexagonal_kcheck.py`、`hexagonal_kcheck.csv`。`README.md` 改动前备份 `README.md.20261111.bak`。

确定性：倒格矢与相位到 k 的映射 **推导**（基于 `M0`/`K0` 与超胞尺寸定义，[IEEE J. Microw. 3(4), 2023 附录 A](https://ieeexplore.ieee.org/document/10256254/)）；10 个配对的计算结果 **已核验**（本脚本实测）；`star of M/K` 中文译名 `[术语未验证]`；**在该残差表的跨 M/K 配对条件下**物理闭合未观测到。按 [Fig. 13(d)](https://ieeexplore.ieee.org/document/10980079/) 反推后的结果见下节。

## 按 Fig. 13(d) 反推 M 点组合（2026-11-11 深夜，已完成）

`dev_history/hexagonal_mpairs.py` 枚举八组谱的全部已求解相位点，计算 SC 帧 k，模 PC 倒格矢折回，判定是否落在 M 等价点集（`M0` 的六个 60° 旋转像，`star of M` 中文译名沿用上节 `[术语未验证]`）。无新仿真。

### 落在 M 的谱点（仅 6 个）

| 谱 | 相位 (deg) | k (rad/mm) | M 等价点索引 | f1 (GHz) |
|---|---|---|---|---|
| `full_GM` | 360 | (0, 1.2092) | 0 | 9.371189 |
| `x_mm` | 360 | (0, 1.2092) | 0 | 9.353546 |
| `x_ee` | 0 | (2.0944, 0) | 0 | 9.371219 |
| `y_ee` | 0 | (0, 1.2092) | 0 | 9.368432 |
| `x_em` | 180 | (1.0472, 0.6046) | 5 | 34.230805 |
| `x_me` | 180 | (1.0472, 0.6046) | 5 | 32.998076 |

`full_GM@360` 的 k 恰为 `M0`，再次印证 SC 的 `φy=2π` 折回原胞 M 点。`x_ee@0` 的 k=(2.0944,0) 模倒格矢折回后同样落到 M 等价点。

### k 一致且频率一致的配对

15 对候选中，7 对同时满足 k 模倒格矢等价且最小频差小于 0.02 GHz。

| 配对 | 最小频差 (GHz) |
|---|---|
| `full_GM@360` 对 `x_ee@0` | 0.0000 |
| `full_GM@360` 对 `y_ee@0` | 0.0028 |
| `x_ee@0` 对 `y_ee@0` | 0.0028 |
| `x_mm@360` 对 `y_ee@0` | 0.0070 |
| `x_em@180` 对 `x_me@180` | 0.0113 |
| `full_GM@360` 对 `x_mm@360` | 0.0176 |
| `x_mm@360` 对 `x_ee@0` | 0.0177 |

### 结论与修正

上一节「物理闭合零例」**只在残差表给定的跨 M/K 配对条件下成立**。按 Fig. 13(d) 反推后，M 等价点上的谱点确实存在 k 一致且频率一致的配对，低频约 9.37 GHz 一组、高频约 39 GHz 一组。这定位了 M 点的物理模式，属于自洽性验证。

**Γ-M-K-Γ 路径在 M 处仍未闭合**。M→K 段的采样点 `φx=120°` 落在 K 等价点，不在 M 点，因此该段起点不能与 Γ→M 段终点（M 点）配对。39 GHz 残差表的判定维持：`x_em@180` 在 M，`y_even@120` 在 K，跨点频率接近属巧合。可发表性结论不变。

文件：`dev_history/hexagonal_mpairs.py`、`hexagonal_M_points.csv`、`hexagonal_M_pairs.csv`。`README.md` 改动前备份 `README.md.20261111-2.bak`。

确定性：6 个 M 点谱点与 15 对配对 **已核验**（本脚本实测）；M/K 等价点集与折回规则 **推导**（基于倒格矢定义与 [IEEE J. Microw. 3(4), 2023 附录 A](https://ieeexplore.ieee.org/document/10256254/)）；配对是否为同一本征模 **未知**（需场型或 parity 对应）；Γ-M-K-Γ 路径闭合在当时采用的 M→K 方向下 **未成立**，方向修正后见下节。

## M→K 方向修正与最终接点（2026-11-12 凌晨，M 点闭合）

`dev_history/hexagonal_path_fold.py` 对 Γ→K1 路径每个 `φx` 计算 SC 帧 k 与 M/K 等价点集归属。**根因**：此前把 `φx=120°` 放在 M 端、`φx=0` 放在 K 端，M→K 段方向反了。

| 谱点 | k (rad/mm) | 归属 |
|---|---|---|
| `y_ee@0`（`φx=0`，`φy=2π`） | (0, 1.2092) | M，等于 `M0` |
| `y_ee@120` | (0.6981, 1.2092) | K 等价点 |
| `y_mm@240`（`φx=4π/3`） | (1.3963, 0) | K，等于 `K0` |

修正后的分段（[Appendix B](https://ieeexplore.ieee.org/document/10980079/)）：Γ→M 用全超胞 `φy` 0 到 π（SC 0 到 2π 折叠），终点 `φy=2π` 为 M；M→K 用 `y_ee` 的 `φx` 0 到 2π/3；K→Γ 用 `y_mm` 的 `φx` 4π/3 到 0。

### 接点判定

| 接点 | 两侧 | k 判定 | f1 差 (GHz) | 结论 |
|---|---|---|---|---|
| M | `full_GM@360` 9.371189 对 `y_ee@0` 9.368432 | 同为 (0, 1.2092)，`same_k=True` | **0.002757** | **M 点闭合** |
| K | `y_ee@120` 29.326815 对 `y_mm@240` 26.836335 | 模倒格矢等价，同落 K 等价点集 | **2.490480** | 未闭合 |

K 点全部 12 模的最优配对为 0.068615 GHz，属跨模式频率接近，需场型或本征模对应才能算闭合，本轮不计入。

### 即时修正

此前「物理闭合零例」「Γ-M-K-Γ 路径在 M 处仍未闭合」是在反了的 M→K 方向下得出。按 Fig. 13(d) 修正方向后，**M 点已严格闭合**（k 一致且最低分支频率一致）。K 点仍差 2.49 GHz，[Appendix B](https://ieeexplore.ieee.org/document/10980079/) 的复模态 HFSS ES 拿不到，可发表性结论不变。

文件：`dev_history/hexagonal_path_fold.py`、`hexagonal_path_fold.csv`、`hexagonal_path_junctions.csv`、`dev_history/hexagonal_gmk_final.py`、`hexagonal_GMK_final.png`、`hexagonal_GMK_final_junctions.csv`。文档改动前备份 `README.md.20261112-3.bak`。

确定性：Γ→K1 各 `φx` 的 k 与 M/K 归属 **已核验**（本脚本实测）；两处接点的 k 等价与频率差 **已核验**；M 点闭合 **已核验**；K 点 0.068615 GHz 跨模式配对是否为同一本征模 **未知**；完整可发表性 **未达成**。

## K 点 parity 对应判定（2026-11-12 凌晨，断点归因）

不需要场型导出（该路径在本工作区已验证不可靠）。parity 标签由对称面组合严格给出：`M^y_0 M^y_{p_y/2}` 为 even、`E^y_0 E^y_{p_y/2}` 为 odd。用全超胞在 `K0` 的谱作模式基准即可判定。

基准谱 `full_GK1@240`（无对称面，含所有 parity）为 26.805988、29.538568、33.392354、33.714311、34.027614 GHz。

| parity | 分支 | f (GHz) | 对应全超胞模 | 差 (GHz) |
|---|---|---|---|---|
| even (`M·M`) | 1 | 26.8363 | mode1 26.8060 | 0.0303 |
| even (`M·M`) | 2 | 33.3920 | mode3 33.3924 | 0.0004 |
| odd (`E·E`) | 1 | 29.3268 | mode2 29.5386 | 0.2118 |
| odd (`E·E`) | 2 | 33.7127 | mode4 33.7143 | 0.0016 |

even 分支依次对应全超胞奇数序号模（1、3、5、7、9），odd 分支对应偶数序号模（2、4、6、8、10）。**2.490480 GHz 是 odd 第一分支与 even 第一分支之差，两者是不同本征模**。

### 即时修正

方向修正节里「K 点 2.490480 GHz 未闭合」是跨 parity 分支比较，属**分支选错**，不代表同模断点或物理带隙。K 点谱自身自洽：even 第一分支与全超胞 mode1 只差 0.0303 GHz。以本节结论为准。

### 路径覆盖限制

| y 方向谱 | 访问的高对称点 |
|---|---|
| even (`y_mm`) | Γ（`φx=0`）、K（`φx=240`） |
| odd (`y_ee`) | M（`φx=0`）、K（`φx=120`） |

没有单一 parity 同时覆盖 M→K 与 K→Γ。Γ→M 与 M→K 由 odd 谱连接，K→Γ 由 even 谱连接，parity 必须在 K 点交叉。[Fig. 16(b)](https://ieeexplore.ieee.org/document/10980079/) 显示 K 附近确有多支模汇合（前向、后向与复模态），现有四组 y 方向组合不足以给出单 parity 连续路径。要严格闭合 K 点，需补 Fig. 15(c)(d) 的 y 方向混合组合 `E^y_0 M^y_{p_y/2}` 与 `M^y_0 E^y_{p_y/2}`（对应 `φy=π`），或取得复模态分类。可发表性仍未达成。

文件：`dev_history/hexagonal_k_parity.py`、`hexagonal_K_parity.csv`、`hexagonal_K_parity_path.csv`。文档改动前备份 `README.md.20261112-4.bak`。

确定性：K 点 parity 分解、模式序号对应、路径访问点 **已核验**（本脚本实测）；K 点需要 parity 交叉的成因 **推断**；混合组合能否提供单 parity 路径 **未知**。

## y 方向混合对称面组合（2026-11-12 上午，已完成，覆盖判定为否）

按 [Fig. 15(c)(d)](https://ieeexplore.ieee.org/document/10980079/) 补 `E^y_0 M^y_{p_y/2}`（em）与 `M^y_0 E^y_{p_y/2}`（me），对应 `φy=π`。`dev_history/hexagonal_symy_mixed.py` 复用 y 方向半超胞几何，两组各用独立 design（`hexagonal_sym_y_em`、`hexagonal_sym_y_me`），x 方向保留 Lattice Pair 扫 `φx` 0 到 4π/3。

| 项 | 结果 |
|---|---|
| 单点校验 | em 23.514604、me 23.948919 GHz，对全超胞 `(φx=0, φy=180)` 的 24.078734 GHz，偏差 0.13 到 0.56 GHz |
| 全扫 | 两组各 9 点，共 18 点全部出数 |
| 失败样本 | probe 已保存边界，全扫重复创建同名 `SymY0_em` 触发 duplicate boundary name；加幂等检查后解决 |

### 高对称点覆盖

| 谱 | 访问的高对称点 | 单 parity 覆盖 M-K-Γ |
|---|---|---|
| even `M^y·M^y` | Γ、K | 否 |
| odd `E^y·E^y` | M、K | 否 |
| em `E^y·M^y` | 仅 M（`φx=180`） | 否 |
| me `M^y·E^y` | 仅 M（`φx=180`） | 否 |

em/me 混合组合在 `φx=180` 时 k=(1.0472, 0.6046)，落在 M 等价点集，f1 分别 37.288815 与 35.772223 GHz。其余 16 个采样点均不落 M/K/Γ（到 K 星与 Γ 的最小距离都是 0.6046）。这与 x 方向 `x_em@180` / `x_me@180` 的 k 一致，构成 M 点高频分支的交叉验证。

**结论**：补齐 Fig. 15 四组 y 方向组合后，仍无单一 parity 覆盖 M→K→Γ。K 点的 parity 交叉是物理必需，或需要 [Appendix B](https://ieeexplore.ieee.org/document/10980079/) 的复模态分类与 MMTMM 本征解。卡点已从采样不足转为方法层面，HFSS Eigenmode 实频 `.eig` 加对称面链路无法给出可发表的完整 Γ-M-K-Γ 色散图。

文件：`dev_history/hexagonal_symy_mixed.py`、`hexagonal_symy_em.csv`、`hexagonal_symy_me.csv`、`dev_history/hexagonal_ymixed_path.py`、`hexagonal_ymixed_path.csv`、`hexagonal_ymixed_summary.csv`、`hexagonal_symy_mixed.log`。文档改动前备份 `README.md.20261112-5.bak`，工程备份 `tensor_patch.aedt.20261112-2.bak`。

确定性：18 点频率、单点校验、高对称点归属与覆盖汇总 **已核验**（本会话实测）；Fig. 15 混合组合规则 **已核验**（PDF 原文）；K 点 parity 交叉的成因 **推断**；可发表性 **未达成**。

## Driven 反演复波数尝试（2026-11-12 上午，第 2 步未通过，按计划回退）

### 第 1 步官方核验（通过）

| 依据 | 结论 |
|---|---|
| [Ansys Help, Assign Floquet Ports](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/AssignFloquetPorts.htm) | `Floquet port` 须沿 Z 轴，相邻边界必须是 linked boundaries，需指定 A/B 晶格向量 |
| [Ansys Help, HFSS Floquet Ports Introduction](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v251/en/Subsystems/HFSS/Subsystems/HFSS%20Floquet%20Ports/Content/Introduction.htm) | 仅 DrivenModal 项目可用；S 矩阵关联 Floquet modes；**不支持 Fast sweep**，仅 Discrete/Interpolating |
| [Ansys 官方教程 PDF](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v261/en/PDFs/HFSS%20Floquet%20Ports.pdf) | 菱形晶格加 Primary/Secondary 加顶面 `Floquet port` 与底面 Wave port 的可运行配置 |
| PyAEDT 1.4.0 官方库 | 存在 `create_floquet_port`、`create_open_region`、`export_touchstone`、`create_linear_count_sweep` |

### 第 2 步探针（未通过）

`dev_history/hexagonal_driven_probe.py` 新建 design `hexagonal_driven_probe`（DrivenModal），矩形超胞保留 4 对 Lattice Pair 与圆盘贴片，去掉 Eigenmode 的 PEC 顶盖，顶面赋 `Floquet port`（modes=2，A/B 向量沿 Lx/Ly），`HFSSDriven` setup 17 GHz 加 15 到 19 GHz Discrete sweep 9 点。

| 检查 | 结果 |
|---|---|
| 几何与边界 | 7 对象、7 边界（含 `FloquetTop`）赋值成功 |
| `validate_simple` | **False** |
| `analyze_setup` | **False**，4.5 s 返回 |
| `export_touchstone` | gRPC 抛 `ExportNetworkData`，属无解后的连带失败 |
| 原生 `ValidateDesign` | **False**，当前 gRPC 通道不返回验证消息 |

`app.excitations` 属性不存在（改用边界名检查）已修，不影响验证结果。

### 未验证的成因假设

`Floquet port` 自身按扫描角定义入射波相位，与 4 对 Lattice Pair 的 `InputPhaseDelay` 变量可能冲突；官方教程配的是 Primary/Secondary 而非 Lattice Pair，且用双端口 FSS 配置，本探针只有单端口加 PEC 地板。三项均为假设，未验证。

按执行计划第 2 步「不通过即停手回退路线 2」，本轮到此停止，没有进入第 3 到 7 步，没有生成任何 S 参数或复波数结果。

诊断问题：需要在 AEDT GUI 打开 `hexagonal_driven_probe` 读取 Validation 消息窗口，或改用官方教程的 Primary/Secondary 加双端口配置重建探针，才能定位验证失败的具体项。

文件：`dev_history/hexagonal_driven_probe.py`、`hexagonal_driven_probe.log`。文档改动前备份 `README.md.20261112-6.bak`，工程备份 `tensor_patch.aedt.20261112-4.bak`，探针脚本备份 `dev_history/hexagonal_driven_probe.py.20261112.bak`。

确定性：官方端口约束与 PyAEDT API **已核验**（官方页与本地库）；探针的 validate/analyze/export 失败 **已核验**（本会话实测）；失败成因 **推断**；S 参数反演复波数 **未执行**；复模态能否补上 K 点 **未知**。

## 六边形调制超胞带隙（2026-11-12 上午，已完成）

Driven 探针失败后按计划回退路线 2。在现有 `hexagonal` design 内把中心圆盘的 `disc_r` 改为 AEDT 表达式 `1.2mm*(1+M)`，四角 1/4 圆扇形片是固定多段线不受影响，于是两个格点半径不等，形成二聚化。Optimetrics `SweepModulation` 同扫 `M`（0、0.1、0.2、0.3）与 `phi_y`（0、90、180 deg），12 个 variation 全部出数，用时 5 分 1 秒。结果走 `Eigen1_IBZ : LastAdaptive` 加 `ListVariations` 求解前后差集导出。

### 最低两分支频差 (GHz)

| M | `phi_y`=0 | `phi_y`=90 | `phi_y`=180 |
|---|---|---|---|
| 0.0 | 0.002842 | 1.031421 | 0.072570 |
| 0.1 | 0.004987 | 1.049705 | 0.375066 |
| 0.2 | 0.015949 | 1.092106 | 0.143861 |
| 0.3 | 0.606519 | 1.211857 | 1.237883 |

Γ 点（`phi_y`=0）的近简并对随 M 单调劈裂，从 0.002842 增至 0.606519 GHz，与二聚化打开频率间隙的预期一致。`phi_y`=90 同样单调，从 1.031421 增至 1.211857 GHz。

**辩证核查**：区边界 `phi_y`=180 的频差非单调（0.0726 到 0.3751 到 0.1439 到 1.2379）。f1 随 M 单调下降（24.072 到 22.469），但 f2 在 M=0.3 由 23.033 回升至 23.707，疑似模式换序。4 个 M 值不足以判定，需加密采样或场型确认，不能写成「区边界带隙随 M 单调打开」。

### 与既有基线对照（口径不同，只作定性）

| 案例 | M=0 带隙 (GHz) | M=0.3 带隙 (GHz) |
|---|---|---|
| 方贴片 8 单元 gap 正弦调制，区边界 | 0.000965 | 0.063781 |
| 圆形开槽 8 单元半径调制，区边界 | 0.001761 | 0.163989 |
| 本案例二聚化，区边界 `phi_y`=180 | 0.072570 | 1.237883 |
| 本案例二聚化，Γ 点 `phi_y`=0 | 0.002842 | 0.606519 |

本案例用 2 格点二聚化，既有基线用 8 单元正弦调制；分支频段也不同（本案例 22 到 24 GHz，基线约 11 GHz）。数值差异不能只归因于晶格类型。

限制：M 只有 4 个值；NumModes=12 按序号取 mode1/mode2，密集模式族下可能混分支；Eigenmode 禁辐射边界与频变材料（[Ansys Help](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/AddinganEigenmodeSetup.htm)）；Driven 漏波未做。

文件：`hexagonal_modulation.py`、`hexagonal_modulation.csv`、`hexagonal_modulation_gap.csv`、`hexagonal_modulation_gap.png`、`hexagonal_modulation.log`、`eig_hexagonal_modulation/`。文档改动前备份 `README.md.20261112-7.bak`，工程备份 `tensor_patch.aedt.20261112-6.bak`。

确定性：12 个 variation 频率、Γ 点单调劈裂、区边界非单调 **已核验**（本会话实测）；区边界非单调的成因 **推断**；与其他案例带隙数值的可比性 **推断**。

## 文件清单

> 本目录仅保留 4 个规范化脚本：`hexagonal_patch.py`、`hexagonal_rect.py`、`hexagonal_ibz.py`、`hexagonal_modulation.py`。其余探索性脚本（`hexagonal_ws.py`、`hexagonal_diagnose.py`、`hexagonal_sym*.py`、`hexagonal_gmk*.py`、`hexagonal_kcheck.py`、`hexagonal_mpairs.py`、`hexagonal_path_fold.py`、`hexagonal_k_parity.py`、`hexagonal_symy_mixed.py`、`hexagonal_driven_probe.py`、`hexagonal_ibz_full.py`、`hexagonal_ymixed_path.py`）已移至 `dev_history/`。
> `.aedt` / `.aedtresults/` / `eig*/` / `*.log` 等未提交仓库（见根目录 `.gitignore`），均由脚本运行时生成，可重建。本文档多处 `*.bak`（含 `.workbuddy/backups/...`）为本地回滚备份，未纳入仓库。

| 文件 | 用途 |
|---|---|
| `hexagonal_patch.py` | 菱形原胞建模、单点、张量扫描、Γ→M 色散（规范化脚本，在本目录）|
| `tensor_patch.aedt`（运行时生成，未提交仓库）| 主工程，新增 design `hexagonal` |
| `hexagonal_xeff_points.csv` / `hexagonal_lightline.png` | 15 点 f(β) 与光锥对比 |
| `hexagonal_dispersion.csv` / `hexagonal_dispersion.png` | Γ→M 段 7 点色散 |
| `hexagonal_xeff.csv` / `hexagonal_fit.csv` | 未生成（反解未通过判据） |
| `hexagonal.log`（运行时生成，未提交仓库）/ `eig_hexagonal/`（`.eig` 未提交仓库）| 运行留痕与官方 `.eig` |

工程改动前曾在本地备份为 `.workbuddy/backups/tensor_patch/tensor_patch.aedt.20261109-6.bak`（**本地备份，未纳入仓库**）。其余 design 与 `ideal_tensor.aedt` 未改动。

## 来源与确定性

一手：[IEEE TAP, document 10256254](https://ieeexplore.ieee.org/document/10256254/)、[IEEE, document 10980079](https://ieeexplore.ieee.org/document/10980079/)（矩形超胞折中）、[Opt. Express 25, 20757 (2017)](https://doi.org/10.1364/OE.25.020757)、[Ansys Help, Adding an Eigenmode Setup](https://ansyshelp.ansys.com/public//Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/AddinganEigenmodeSetup.htm)。

确定性：建模、`validate_simple`、Γ 点 12 个频率、15 点与 7 点扫描频率 **已核验**（本会话实测）；六边形 HFSS 相位设置 **已核验**（IEEE 论文原文）；V 向量方向是否正确 **未知**；C6v 各向同性在本几何是否成立 **未知**；β≤k0 的成因 **推断**。
