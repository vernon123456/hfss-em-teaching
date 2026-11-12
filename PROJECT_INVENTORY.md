# HFSS 表面波/周期结构教学案例集 — 盘点与 GitHub 准备

> 生成日期：2026-11-12。数据来源：本工作区各案例实测结果与 `MEMORY.md`。确定性：案例结果与文件体积均**已核验**（本会话实测）；跨案例对比与根因标注**推断**处已显式标明。

---

## 一、案例总览

共 **6 个已完成案例** + **1 个未竟探索**（Driven 复波数尝试，未成案例）。

| # | 目录 | 主题 | 状态 | 一句话结论 |
|---|---|---|---|---|
| 1 | `scalar_impedance_eigenmode/` | 标量阻抗面最小案例 | 达成 | 7 点色散最大误差 0.425%，验证基准成立 |
| 2 | `patch_unitcell/` | 接地方贴片单元（Fong 2010） | 达成（主值） | Xs 反解 239.8→147.3 Ω；大 gap 偏差 8.5~9.8% 根因未定位 |
| 3 | `tensor_patch/`（`parametric`+`ideal_tensor`） | 切片方贴片张量阻抗面 | 部分达成 | 主轴角随 θ_s 单调，端点偏差 17~23° 根因未定位 |
| 4 | `tensor_patch/`（`supercell`） | 调制阻抗超胞带隙（8 单元 gap 正弦） | 达成 | M=0→0.3 区边界带隙 0.0010→0.0638 GHz 单调打开 |
| 5 | `tensor_patch/`（`circular`+`circular_supercell`） | 开槽圆贴片单元 | 达成（优于方切片） | 主轴角端点偏差 ≤2.2°；超胞带隙 0.0018→0.1640 GHz |
| 6 | `tensor_patch/`（`hexagonal` 及子实验） | 六边形排列（矩形超胞） | 未达可发表 | M 点严格闭合 0.002757 GHz；K 点需复模态，HFSS ES 拿不到 |
| — | `tensor_patch/`（`hexagonal_driven_probe`） | Driven Floquet 反演复波数 | 失败/回退 | 第 2 步 validate/analyze 失败，未产出 S 参数 |

---

## 二、逐案例详述

### 案例 1 — 标量阻抗面最小案例
- **功能**：最小可运行闭环。PEC 底板 + 理想 sheet 阻抗面，Eigenmode 扫相位求表面波色散，与闭式基准对比。
- **运行效果**：7 相位点全流程约 3.5 min；最大误差 0.425%，平均 0.149%；损耗情形 Rs=20 Ω/□ 时 Q 由 ~1e12 降至 22.75。
- **是否达预期**：是。
- **有效性评估**：高。本案例确立了后续全部案例的提取链路（`ExportEigenmodes` 正确路径、`.eig` 解析、色散不用扫频而用 Lattice Pair 相位），是整套教学的基础。
- **验证基准**：β_sw = k0·√(1+(Xs/η0)²)；两源交叉验证 Casaletti 2016 式(2)、Sci Rep 2020 式(11)。

### 案例 2 — 接地方贴片单元（Fong 2010）
- **功能**：实物方贴片单元（p=3 mm, h=1.57 mm, εr=2.2），Eigenmode 扫相位反解 17 GHz 处 Zs；介质/空气共面侧壁需 4 对 Lattice Pair。
- **运行效果**：Xs 由 239.8 降至 147.3 Ω（g 0.2→1.0 mm）。小 gap 与 Fong 234 / Opt. Express 245.7 Ω 差 ±2.5%；大 gap 比 161 / 163.4 Ω 低 8.5~9.8%。理想 sheet 闭环偏差 0.0089%。
- **是否达预期**：基本达成，大 gap 偏差未解释。
- **有效性评估**：中高。方法链路成立且精度高，但大 gap 偏差根因未定位（候选：网格收敛、工作点口径、模式识别），作为教学示例需标注为「开放问题」。
- **引用**：Fong & Itoh, *IEEE TAP* 58(9), 2010。

### 案例 3 — 切片方贴片张量阻抗面
- **功能**：实物方贴片加斜切片（g_s, θ_s），5 个传播方向反解 X_eff(θ) 后最小二乘拟合张量 Zxx/Zxy/Zyy；理想 `Anisotropic Impedance` 边界闭环验证。
- **运行效果**：主轴角随 θ_s 单调 23.3→46.0→56.6→72.6°，θ_s=45 近重合，两端偏差 17~23°；理想边界 5 方向 HFSS 频率误差 ≤0.504%。
- **是否达预期**：部分达成。
- **有效性评估**：中。几何与反解流程跑通，但端点偏差与 Fong 论文主轴角不符，根因未定位；二次型近似（n≈1.1）在 n>5 失效区不可用。适合展示「方法」，不宜作为「完美吻合」示例。
- **引用**：Fong 2010 式(17)；US 7911407（≥3 方向 + 最小二乘）。

### 案例 4 — 调制阻抗超胞带隙（8 单元 gap 正弦）
- **功能**：8 单元 Λ=24 mm 超胞，gap_i = gmid·(1+M·cos(2πi/N))，Optimetrics 同扫 M 与超胞相位，取最低两分支频差。
- **运行效果**：M=0/0.1/0.2/0.3 区边界带隙 0.0010 / 0.0240 / 0.0404 / 0.0638 GHz，随 M 单调打开，M=0 基本闭合。约 7 min。
- **是否达预期**：是。
- **有效性评估**：高。复用已验证链路产出独立结果，口径清晰。限制：NumModes=8 仅覆盖 ~10~16 GHz（非 17 GHz 主模）、调制为几何 gap 正弦而非严格阻抗正弦、phi=30°/M=0.3 处 mode2 换序、Eigenmode 禁辐射。

### 案例 5 — 开槽圆贴片单元
- **功能**：圆盘穿心矩形槽，扫槽角反解主轴角；同建圆形超胞看带隙。
- **运行效果**：主轴角随槽角精确跟随（0→-1.78、45→45.42、90→-89.36°），端点偏差 ≤2.2°，明显优于方切片；二次型残差 0.26~0.64 Ω。超胞带隙 M=0→0.3 为 0.0018→0.1640 GHz。
- **是否达预期**：是，且优于案例 3。
- **有效性评估**：高。是六个案例中「几何对称性→张量主轴」关系最干净的演示，推荐作为张量面教学的首选。限制：双谐振未显式观测、超胞只扫区边界点、退化校验非严格无槽圆盘。

### 案例 6 — 六边形排列（矩形超胞）
- **功能**：菱形 WS 原胞→矩形超胞（Lx=3 mm, Ly=√3a），中心圆盘 + 四角 1/4 圆扇形，4 对 Lattice Pair，IBZ 两段相位扫描取 Γ-M-K-Γ。
- **运行效果**：M 点严格闭合（full_GM@360 对 y_ee@0，k 同为 (0,1.2092)，f1 差 0.002757 GHz）；K 点用奇偶对称面组合判定，2.49 GHz 差属跨 parity 分支选错而非物理带隙。子实验：六边形调制超胞（2 格点二聚化）Γ 点单调劈裂 0.002842→0.606519 GHz，区边界非单调。
- **是否达预期**：否（未达可发表完整 Γ-M-K-Γ）。
- **有效性评估**：中。方法层面卡点已定位——HFSS Eigenmode 实频 `.eig` 加对称面链路无法给出 K 点复模态，需论文的 MMTMM 本征解或 Driven 复波数（当前工具链缺）。作为「失败案例/方法边界」教学有价值，但须明确标注不可发表。
- **引用**：IEEE TMTT 73(9), 2025（IBZ 相位关系、MMTMM 复模态）；论文 Fig.13/15 对称面规则。

### 未竟探索 — Driven Floquet 复波数
- 第 1 步官方核验通过（Ansys Help Assign Floquet Ports、官方教程 PDF、PyAEDT `create_floquet_port` 存在）。
- 第 2 步探针 `hexagonal_driven_probe`：validate_simple=False、analyze=False、export_touchstone 抛 ExportNetworkData。按计划停手回退。
- **价值**：留下可复用的官方端口设置依据与失败证据，作为「换求解器」方向的方法笔记。

---

## 三、文件结构盘点与分类

### 体积事实（已核验）
- 工作区总计 **2.7 GB / 16246 文件**。
- 重型文件全部是可再生仿真产物：`.aedtresults/` 2.4G（tensor_patch）+ 176M（patch）+ 67M（ideal_sheet）；`.aedt` 工程（二进制，数百 MB）。
- 教学所需的小文件：脚本 26 个、CSV 51 个、PNG 20 个、README 6 个、SVG 1 个，合计约 20 MB 量级。

### 分类原则
- **核心必要（保留并纳入 GitHub）**：各案例 canonical 构建/扫描脚本、README、结果 CSV/PNG/SVG、1~2 个 `.eig` 样例。
- **可删除/忽略（P1，均可由脚本重生成）**：`*.aedt`、`*.aedtresults/`、`*.pyaedt`、`*.log`、`eig*/`、`__pycache__`、`*.lock`、`.sd/.ngmesh/.stats/.g3derr/.info`。
- **开发历史（建议移入 `dev_history/`，不纳入教学主线）**：hexagonal 系列的探索脚本 `gmk/gmk_v2/gmk_v3/gmk_final`、`hexagonal_ws`、`hexagonal_diagnose`、`hexagonal_driven_probe`、`hexagonal_sym*`(早期)、`hexagonal_kcheck/mpairs/path_fold/k_parity/ymixed_path` 等——这些是求解轨迹，非教学核心。

### 各案例核心文件清单
| 案例 | 核心脚本 | 核心结果/文档 |
|---|---|---|
| 1 | `build_and_run.py` | `README.md`, `dispersion.csv/png/svg`, `eig_50.eig`(样例) |
| 2 | `patch_unitcell.py`, `ideal_check.py` | `README_patch.md`, `Z_vs_g.csv/png`, `Xs_by_mode.csv`, `ideal_dispersion.csv`, `ideal_compare.png` |
| 3 | `parametric_scan.py`, `ideal_tensor_check.py` | `README_tensor.md`, `Xeff_by_angle.csv`, `dispersion_M.png` |
| 4 | `supercell_scan.py` | `README_supercell.md`, `bandgap_vs_M.csv/png` |
| 5 | `circular_patch.py`, `circular_supercell.py` | `README_circular.md`, `circular_xeff.csv`, `circular_fit.csv`, `circular_axis.png`, `circular_bandgap_vs_M.csv/png` |
| 6 | `hexagonal_patch.py`(或 `hexagonal_rect.py`), `hexagonal_ibz.py`, `hexagonal_modulation.py` | `README_hexagonal.md`, `hexagonal_ibz.csv`, `hexagonal_dispersion.png`, `hexagonal_ibz_dispersion.png`, `hexagonal_GMK_final.png`, `hexagonal_M_pairs.csv` |

---

## 四、清理方案（打包最小集）

**必留**：上述核心脚本 + README + 结果 + 每案例 1 个 `.eig` 样例 + 根 `.gitignore` + 本文件。
**建议删除/忽略**：
- `tensor_patch/tensor_patch.aedtresults/`（2.4 GB，第一优先）
- `patch_unitcell/patch_unitcell.aedtresults/`（176 MB）、`ideal_sheet.aedtresults/`（67 MB）
- 所有 `*.aedt`、`*.pyaedt`
- 所有 `*.log`、`eig*/` 目录、`__pycache__`
- 探索脚本移入 `tensor_patch/dev_history/`

清理后预计体积从 2.7 GB 降至约 **20~30 MB**，可直接 `git add` 纳入。

---

## 五、GitHub 目录组织建议

```
hfss-em-teaching/                # 仓库根
├── README.md                    # 总览、环境、安装、案例索引、引用/致谢
├── LICENSE
├── .gitignore
├── common/
│   └── env_bootstrap.py         # ANSYSEM_ROOT261/AWP_ROOT261 注入、版本、端口说明片段
├── 01_scalar_impedance_surface/
│   ├── README.md
│   ├── build_and_run.py
│   └── results/{dispersion.csv, dispersion.png, dispersion.svg, eig_50.eig}
├── 02_patch_unit_cell/
│   ├── README.md
│   ├── patch_unitcell.py
│   ├── ideal_check.py
│   └── results/{Z_vs_g.csv, Z_vs_g.png, Xs_by_mode.csv, ideal_dispersion.csv, ideal_compare.png}
├── 03_tensor_sliced_patch/
│   ├── README.md
│   ├── parametric_scan.py
│   ├── ideal_tensor_check.py
│   └── results/{Xeff_by_angle.csv, dispersion_M.png}
├── 04_modulated_supercell/
│   ├── README.md
│   ├── supercell_scan.py
│   └── results/{bandgap_vs_M.csv, bandgap_vs_M.png}
├── 05_slotted_circular_patch/
│   ├── README.md
│   ├── circular_patch.py
│   ├── circular_supercell.py
│   └── results/{circular_xeff.csv, circular_fit.csv, circular_axis.png, circular_bandgap_vs_M.csv, circular_bandgap_vs_M.png}
└── 06_hexagonal_lattice/
    ├── README.md
    ├── hexagonal_patch.py
    ├── hexagonal_ibz.py
    ├── hexagonal_modulation.py
    └── results/{hexagonal_ibz.csv, hexagonal_dispersion.png, hexagonal_ibz_dispersion.png, hexagonal_GMK_final.png, hexagonal_M_pairs.csv}
```
注：案例 3/4/5/6 现同处 `tensor_patch/` 单工程多 design；上传时每个案例只抽取其 canonical 脚本与结果，工程 `.aedt` 不提交（脚本可重建）。`dev_history/` 可选，不放教学主线。

---

## 六、每个案例 README 要点模板

每个 `README.md` 建议包含以下小节（术语按《交付物术语规范》核验，未核验者标 `[术语未验证]`）：

1. **目标**：一句话说明本案例演示什么物理/方法。
2. **物理背景与引用**：原始论文、关键方程编号、本案例与论文的参数差异（实测中多处论文参数不可直接移植）。
3. **模型参数表**：几何尺寸、材料、周期、层高、边界（PEC 地板/顶盖、Lattice Pair 相位变量）。
4. **求解设置**：Eigenmode、MinFreq、NumModes、是否 Save Fields、网格注意点。
5. **运行步骤**：`python <script>.py`，环境变量注入说明，预计耗时。
6. **预期结果**：关键数值（如 Xs 区间、带隙宽度、主轴角），与闭式/论文的对比误差。
7. **验证基准**：公式与来源链接。
8. **已知限制与开放问题**：明确标注未解释偏差、NumModes 覆盖频段、Eigenmode 禁辐射、方法边界（六边形 K 点复模态）。
9. **文件索引**：脚本→结果→样例 `.eig` 的对应。

---

## 七、遗留问题与后续

- **六边形可发表性**：需复模态/MMTMM（当前工具链缺关键组件）；或先按论文实现 Driven 双端口 Floquet 取 S 参数反演（探针已失败，待重建双端口配置）。
- **跨案例带隙对照**：口径不同（2 格点二聚化 vs 8 单元正弦、22~24 GHz vs 11 GHz），只能定性，README 须标注。
- **大 gap 偏差（案例 2）/ 端点偏差（案例 3）**：根因仍未定位，作为教学开放问题保留。
- **备份基线**：`tensor_patch.aedt.20261112-6.bak`（1137769 bytes）；`.workbuddy/backups` 共 17 MB / 79 文件。清理前建议先确认备份完整。
