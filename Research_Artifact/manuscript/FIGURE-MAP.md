# 图与编辑入口

PDF 实际图号按正文引用顺序排列，文件编号不等同于 PDF 图号。

| 位置 | 图文件（省略扩展名） | 脚本入口 | 内容 |
|---|---|---|---|
| 正文 Fig. 1 | f01_gap | figure_sources/gap_figure.py（由 make_figures.py 调用） | 左上：完成记录缺口；左下：内容不变时的三类独立变化；右：对应真实源码节选 |
| 正文 Fig. 2 | f02_overview | make_figures.py / diagrams | 整体流程 |
| 正文 Fig. 3 | f04_ownership | make_figures.py / diagrams | 逻辑归属与物理尝试 |
| 正文 Fig. 4 | f03_validity | make_figures.py / diagrams | 证据生成与有效性检查 |
| 正文 Fig. 5 | f05_validity | make_figures.py / experiments | 安全、分支、消融、生命周期 |
| 正文 Fig. 6 | f06_recovery | make_figures.py / experiments | 恢复、完整过程、调用次数及区间 |
| 正文 Fig. 7 | f07_cost | make_figures.py / experiments | 成本分解、范围、阈值、重复请求 |
| 补充材料 | f08_dependencies | figure_sources/dependency_figure.py | 依赖范围与规模 |
| 补充材料 | f09_runtime | make_figures.py / experiments | 运行时组合 |
| 补充材料 | f10_mixture | make_figures.py / mixture | 中断、命中、重复请求成本曲面 |

所有图都提供 PDF、SVG、PNG。PDF 供 LaTeX 引用；SVG 保留文本，便于矢量编辑；PNG 用于预览及 HTML 补充材料。

- 调整数据对应的样式：修改脚本内的颜色、线型、标记、轴标签与子图布局。
- 修改图注：修改正文各章节中的 caption。
- 修改机制示意图中的文字与框图：修改 diagrams 函数中的 box/arrow 调用。
- 图 1 独立生成：`python figure_sources/gap_figure.py`。输出 3.5 × 2.375 英寸单栏矢量 PDF、保留文本的 SVG 和 600 dpi PNG；本版采用三档灰度、统一纯色红色填充以及源码省略标记，见 `../editorial/2026-10-18-figure1-single-column/README.md`。
- 只修改 SVG 后，不要直接运行整套绘图脚本，否则手工修改会被覆盖。
- Figure 8 的输入来自单独的依赖范围实验，不能与主实验批次合并。

figure_manifest.json 记录各图输入文件及 SHA-256。重跑脚本后会重新生成该清单。
