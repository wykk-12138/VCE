# 数据字段与方法对应

## 方法标识

保留原始记录里的标识，以便精确对应汇总代码。显示名变化不会改变数据行。

| 原始标识 | 论文/绘图标签 | 含义 |
|---|---|---|
| `ReceiptCoordinatorV15` | VCE；部分冻结图标为RC-E | 当前依赖范围验证的完成证据机制 |
| `JournalGuardedScoped` | J-Q | 匹配安全条件的查询式Journal |
| `JournalPostStatus` | J-1 | 激活后单次状态查询控制 |
| `JournalWitnessV15` | J-E | 在独立Journal表征上迁移同一证据机制 |
| `ReceiptCoordinatorV14` | Full / RC-F | 全目录树证据验证，用于范围对比 |
| `OriginalReplan` | Replan | 重新预览/部署控制，见组合实验 |

其他早期方法和消融名称保留在各自 `spec.json` 与实现脚本中。历史发表系统实验的作者源码、对接代码及适配记录均在历史包；不将自建Journal控制标为发表模型。

## 主性能记录

| 字段 | 含义 |
|---|---|
| `batch` | b1、b2、b3：三次独立启动的实验批次 |
| `block`、`repository` | 条件内配对的输入/项目标识 |
| `tool` | claude、codex、grok原生适配器 |
| `scenario` | normal、recovery、fallback、completed_retry、unrelated_edit |
| `lifecycle` | cold为新管理进程；warm为已初始化管理进程 |
| `noise` | 额外普通源码文件数量，常见0或2048 |
| `warmup` | 是否预热；合并计分表排除预热 |
| `wall_ns` | 被测确认/恢复调用的外部计时，纳秒 |
| `handler_ns` | 管理器内部处理计时，纳秒 |
| `preview_ns` | 预览耗时，纳秒 |
| `first_ns` | 中断前/已完成的首次确认耗时；fresh路径为0 |
| `confirmation_episode_ns` | first_ns + wall_ns |
| `episode_ns` | preview_ns + first_ns + wall_ns |
| `commands` | 被测调用启动的原生命令序列 |
| `profile` | 原生调用各次计时 |
| `components` | 验证、回读、发布等内部跨度 |
| `evidence_bytes` | 持久化证据大小，字节 |
| `oracle` | 独立检查的磁盘/引用/管理状态与唯一完成身份等结果 |
| `pass` | 该行断言是否通过 |

便捷CSV中的 `*_ms` 为对应纳秒字段除以1,000,000；`native_processes` 为 `commands` 列表长度。完整嵌套信息以JSONL为准。

## 汇总与模型

`facts.json` 的 `comparisons` 以 `tool/scenario/lifecycle/noise` 为键。绝对时延为单元观测的中位数；配对比值为对应比值的几何均值。95%区间来自4,000次项目/批次交叉重采样。不要把两组中位数之比替代已报告的配对估计。

`costs` 使用算术均值计算 fresh/hit/miss/repeat 差值。`mixture_surface.csv` 为根据这些实测均值计算的成本模型网格，并非混合负载的新增实测记录。`sensitivity.csv` 保留逐批/逐项目留一分析。

`domain_thresholds.csv` 来自独立的范围成本实验；依赖选择器v15研究及早期消融也保留各自批次，不并入三批主实验。
