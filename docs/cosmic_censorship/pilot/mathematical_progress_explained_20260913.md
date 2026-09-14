# 宇宙监督猜想 swarm：数学进展的科普式整理

> **阅读提示**：这份说明区分“数学事实”“文献中已有的结果”“本项目的工程/审计结果”和“仍未解决的问题”。swarm 没有证明弱或强宇宙监督猜想；它目前最可靠的产出，是把一个容易被一句口号掩盖的问题拆成了可检查的数学命题，并发现了若干会导致误判的关键漏洞。

## 1. 宇宙监督猜想究竟在问什么？

广义相对论把引力写成时空几何。未知量是度规 $g$，Einstein 方程为

\[
G_{\mu\nu}(g)+\Lambda g_{\mu\nu}=8\pi T_{\mu\nu}.
\]

给定一片初始空间 $\Sigma$ 以及其上的度规 $h$ 和第二基本形式 $K$，它们必须满足 Einstein 约束方程。方程随后决定一个最大的 Cauchy development（最大柯西发展）$\mathcal M$。

“监督”这个词的直觉是：奇点可以存在，但不应当随意暴露给远处观察者。黑洞内部可以有奇点；问题在于，从一个合理的初始状态出发，奇点是否会出现在外部观察者的因果视野中。

这句话至少包含三个不同问题：

1. **奇点是什么？** 是测地线不完备、曲率标量发散，还是某种低正则性下不可延拓？
2. **看见是什么意思？** 到达未来零无穷 $\mathscr I^+$，还是只到有限半径观察者，还是穿过 Cauchy horizon？
3. **“一般初始数据”是什么意思？** 开稠密、残集、满测集，还是某个加权 Sobolev 空间中的稳定性？

因此，“宇宙监督猜想是否成立”不是一个单一二元问题，而是一族 formulation。

## 2. 弱监督和强监督：两个方向

### 2.1 弱宇宙监督（WCC）

弱监督主要关心远处的天文观察者。一个典型的渐近平坦真空版本可以粗略写成：对某个指定的初始数据空间和泛型概念，最大柯西发展在未来零无穷附近不会产生可见的裸奇点。

这里的“可见”常用因果语言表达。例如，若奇点集合为 $\mathcal S$，希望其因果影响不能到达声明的无穷边界：

\[
J^-(\mathscr I^+)\cap \mathcal S=\varnothing,
\]

但这只是示意式写法。真正的定理还要说明 $\mathscr I^+$ 是否存在、其正则性是什么、初始数据的渐近条件是什么，以及“奇点”采用哪种定义。

### 2.2 强宇宙监督（SCC）

强监督关注决定论本身：给定初始数据，最大柯西发展是否还能被延拓？若存在足够规则的非平凡延拓，那么同一组初始数据可能产生不唯一的未来，经典预测能力就会失效。

常见版本包括：

- **$C^2$-不可延拓**：不存在度规 $g'\in C^2$ 的非平凡延拓；
- **$C^0$-不可延拓**：不存在连续度规的非平凡延拓；
- **弱 Einstein 延拓**：延拓虽然低正则，但仍以某种弱解意义满足 Einstein 方程；
- **曲率或 Christoffel 条件**：例如要求 Christoffel 符号不属于 $L^2_{\mathrm{loc}}$，或曲率分布无法保持指定可积性。

这些版本并不等价。一个时空可能 $C^0$ 可延拓，却 $C^2$ 不可延拓；也可能曲率发散，但度规本身仍连续。因此不能把“强监督成立”当成一个不带正则性下标的结论。

## 3. 为什么 formulation family 是本项目最重要的数学进展？

swarm 首先发现，很多看起来互相矛盾的句子，其实回答的是不同问题。当前分类表固定了以下维度：

| 维度 | 例子 | 改变后会发生什么 |
|---|---|---|
| 方程/物质 | 真空、无质量标量、Maxwell、流体 | 解的稳定性和奇点机制会改变 |
| 维数 | $3+1$、高维 | 高维黑环和不稳定性会进入问题 |
| 渐近边界 | AF、de Sitter、AdS | 可见性目标和边界条件不同 |
| 对称性 | 无对称、轴对称、球对称 | 对称约化可能降低难度，也可能改变泛型性 |
| 初始数据空间 | 光滑紧支撑、加权 Sobolev、有限能量 | “一般性”和连续依赖都依赖于拓扑 |
| 奇点概念 | 测地线不完备、Kretschmann 发散、弱零奇点 | 不同概念的蕴含关系并不自动成立 |
| 延拓正则性 | $C^0$、$C^2$、弱 Einstein | SCC 的命题强度不同 |
| 结论类型 | 定理、稳定性、反例、数值迹象 | 证据等级完全不同 |

项目将每条 claim 绑定到一个 class id，例如 `AF-WCC-VAC-GEN`、`AF-SCC-C2-VAC-GEN`、`AF-SCC-C0-VAC-GEN`、`AF-WCC-SCALAR-SPH` 和 `KERR-SCC-INNER`。规则是：没有证明过的跨类蕴含，就不能把一个 class 的结果外推到另一个 class。

这不是文档整理的小修补，而是数学命题的必要组成部分。

## 4. 几何上如何判断“形成了黑洞”？

在球对称或数值相对论中，常见诊断是二维球面的零膨胀。设 $\ell_+$ 和 $\ell_-$ 是向外、向内的两个零方向，球面面积为 $4\pi r^2$，则零膨胀可以写成

\[
\theta_\pm=\frac{1}{4\pi r^2}\,\mathcal L_{\ell_\pm}(4\pi r^2)
=\frac{2}{r}\ell_\pm(r).
\]

陷获面通常满足两个方向的膨胀都为负；边界上的零膨胀则是视界诊断的一部分。球对称中常用 Misner--Sharp 质量 $m$，其关系形如

\[
1-\frac{2m}{r}=g^{ab}\nabla_a r\nabla_b r.
\]

当右侧变为零时，$r=2m$ 是一个重要的几何信号。但它依赖于所研究的模型和对称性，不能把某个坐标中的关系直接当成所有时空的事件视界定义。

同样，Painlevé--Gullstrand 坐标中的

\[
\frac{dr}{dt}=\alpha-\beta
\]

或某个坐标分量 $g^{rr}=0$，只能作为特定规范下的诊断。它们不能单独证明“这里就是事件视界”，更不能由“有限数值盒内没看到视界”推出“存在裸奇点”。

## 5. 为什么曲率不变量比坐标图更可信？

坐标可以把一个完全平滑的几何对象画得很奇怪。因而需要坐标不变量，例如 Kretschmann 标量

\[
K=R_{\alpha\beta\gamma\delta}R^{\alpha\beta\gamma\delta}.
\]

如果 $K$ 在某条曲线上真正发散，这比坐标分量发散更接近几何奇点。不过即使观察到数值上的大 $K$，仍需检查：

- 分辨率加密后峰值是否按可解释的规律变化；
- 约束残差是否同时变大；
- 边界反射、截断误差或 gauge effect 是否制造了假峰；
- 是否存在通向声明的无穷边界的因果射线；
- 扰动初始数据后现象是开放集稳定、余维数现象，还是单条精细调参轨道。

swarm 的早期审计把“坐标 blow-up 当作曲率 blow-up”列为硬错误，并要求至少一个曲率不变量、两种规范诊断、三档以上分辨率以及因果传播测试共同支持候选事件。

## 6. 已有文献结果应该怎样拼接？

当前 literature lane 的改进，是把每条文献记录成五元组：

\[
(\text{source identity},\;\text{quoted claim},\;\text{assumptions},\;\text{class id},\;\text{does-not-prove}).
\]

这使得以下几类结果可以被正确放在各自位置：

- Dafermos--Luk 关于 Kerr Cauchy horizon 的 $C^0$ 稳定性方向；
- Luk、Sbierski 关于弱零奇点和低正则性结构的结果；
- Sbierski 关于曲率 blow-up 与 Lipschitz 不可延拓的结论；
- Hintz 关于次极端 Kerr 非线性稳定性的结果。

这些结果分别讨论不同的背景、扰动类、渐近结构和正则性门槛。把它们串成“所以四维真空宇宙监督猜想已经证明”是逻辑错误；它们更像一张局部地图：某些 Kerr 内部结构在某个正则性意义下稳定，某些延拓会被曲率爆炸阻止，但这不等于覆盖所有渐近平坦真空泛型初始数据。

目前文献门禁 `G-LIT` 仍为 pending，因为最终接受还需要统一 measured hash、distinct reviewer 和逐条原文定位。

## 7. 数值方向到底做了什么？

### 7.1 N0：平直时空标定

允许运行的 N0 是平直背景上的标量波/约束测试。它的作用是校准：

- 演化器是否有预期收敛阶；
- 约束残差是否随分辨率下降；
- 独立复跑是否得到同样的曲线；
- 日志、checkpoint、trajectory 和退出码是否完整。

若误差满足

\[
E(h)\approx C h^p,\qquad
 p\approx\log_2\frac{E(h)}{E(h/2)},
\]

则可以估计数值收敛阶 $p$。这类证据能说明“数值管线工作正常”，不能说明自引力坍缩中出现了裸奇点。

### 7.2 N1：自引力阶段仍然锁定

当前门禁要求

\[
\operatorname{Unlock}(N1)Longleftrightarrow
G_{\mathrm{FORM}}=\mathrm{pass}land
G_{\mathrm{AUDIT}}=\mathrm{pass}land
G_{\mathrm{NUM}}=\mathrm{pass}.
\]

现在 $G_{\mathrm{FORM}}$、$G_{\mathrm{AUDIT}}$、$G_{\mathrm{NUM}}$ 都没有通过，所以 `numerics/spherical_solver` 保持不存在，N1 没有被偷偷启动。这是正确的科学约束：球对称 Einstein--scalar 结果不能直接支持或反驳四维渐近平坦真空 WCC。

## 8. 27 个 fixture 样本说明了什么？

class-separation 回归夹具含 27 个固定案例：

\[
TP=17,\quad FP=0,\quad TN=10,\quad FN=0.
\]

因此在这个固定夹具上：

\[
\widehat{\mathrm{accuracy}}=\frac{17+10}{27}=1,\qquad
\widehat{\mathrm{FPR}}=0,\qquad
\widehat{\mathrm{FNR}}=0.
\]

这个数字的正确解读是：“当前回归测试没有被已知的 27 个分类陷阱击穿。”它不是“模型对所有数学文本的准确率为 100%”。更严格地说，后续审计发现有些 claim 把 detector 自己输出的“composite C0/C2 asserted as one class”重新当成真实数学 claim，存在 self-reference / detector-output contamination 风险。因此 `G-AUDIT` 仍然 pending。

## 9. 目前最值得展示的真实新结果：formulation pin drift

旧的 rev29 frozen manifest 与当前磁盘 schema 的哈希出现漂移：

\[
 h_{\mathrm{disk}}(s)\neq h_{\mathrm{frozen}}(s),qquad
 s\in\{\texttt{AF-SCC-C0},\texttt{AF-SCC-C2}}.
\]

已观察到的前缀包括：

- rev29 的 C2 pin 以 `e9a27996dfd3...` 开头；当前磁盘 C2 schema 以 `c1013e486988...` 开头；
- rev29 的 C0 pin 与当前 C0 schema 也不一致，当前值以 `c4d17fe6ac59...` 开头；
- 多个独立 worker 重复发现这一点，并有 worker 同时验证 primary/mirror 文件仍 byte-identical。

数学上的含义非常直接：在旧 formulation 上做出的 review，不能自动升级成对当前 formulation 的 review。这个发现阻止了一个很常见的错误：文件名相同、内容看起来相似，就假设命题仍然相同。

## 10. 用 Raychaudhuri 方程看“为什么奇点会集中”

对一族零测地线，Raychaudhuri 方程（无扭率时）具有示意形式

\[
\frac{d\theta}{d\lambda}
=-\frac{1}{2}\theta^2-\sigma_{ab}\sigma^{ab}
- R_{ab}k^ak^b.
\]

它说明膨胀 $\theta$ 会受到剪切 $\sigma$ 和 Ricci 曲率的聚焦作用。若满足适当能量条件，零线可能在有限仿射参数内聚焦，形成 trapped-surface 机制。但从“聚焦”到“裸奇点不可见”之间还隔着全局因果结构、初始数据泛型性和延拓正则性等问题。

这正是为什么单个局部方程、单个图像或单个模拟峰值都不够成为 WCC/SCC 定理。

## 11. 当前成果的证据分级

| 层级 | 当前状态 | 能支持的说法 | 不能支持的说法 |
|---|---|---|---|
| 数学背景 | 已整理 | 定义、版本差异、已知文献范围 | 新定理 |
| swarm 研究地图 | G-F0 pass | 命题族和依赖关系内部一致 | 所有字段都已最终冻结 |
| 回归夹具 | 27/27 正确 | 固定夹具未被已知陷阱击穿 | 泛化准确率 100% |
| pin-drift 审计 | 多 worker 重复 | 旧 review 不能冒充当前 review | 数学命题本身被证伪 |
| literature ledger | 结构已建立 | 可审计的引用工作流 | 所有条目已最终验收 |
| N0 calibration | 有收敛/复跑材料 | 管线校准 | 真空 WCC/SCC 证据 |
| 完整 WCC/SCC | 未完成 | 仍是开放研究问题 | 已证明、已反例 |

## 12. 对“蜂群乱舞”的诚实判断

早期五角色 pilot 的结果很有代表性：5/5 角色生成结构化输出，4/4 独立审阅完成，但 F1 formulation 的科学接受率为 $0/1$，hard-failure rate 为 $1/1$，R1 数学正确性约为 $2.4/5$。失败原因不是没有文字，而是把 WCC/SCC、$C^0/C^2$、真空/标量和局部/全局结论混成了一个流畅句子。

因此目前最准确的判断是：

> swarm 已经脱离“完全随机的蜂群乱舞”，因为它能稳定地产生分类、反例清单、证据 tuple 和可重复的 blocker；但它还没有达到“数学研究 oracle”或“可以独立交付定理”的水平。

它现在适合：

- 生成研究地图和精确定义草案；
- 主动寻找 formulation 混淆和过强 claim；
- 做文献范围审计和数值协议设计；
- 为数学合作者准备一份可追溯的 review 包。

它现在不适合：

- 自动宣布 WCC/SCC 已解决；
- 把自然语言输出直接变成定理；
- 用球对称标量实验外推一般四维真空；
- 在 formulation 和 audit 门禁未通过前启动 N1。

## 13. 下一步真正有数学含量的路线

1. **重新冻结 formulation**：为 `AF-WCC-VAC-GEN`、`AF-SCC-C2-VAC-GEN`、`AF-SCC-C0-VAC-GEN` 分别固定假设、拓扑、泛型性和延拓类别，并修复 current/frozen hash split。
2. **完成文献 theorem ledger**：每条 claim 绑定原文页码/定理号、class id、假设和 does-not-prove。
3. **完成 N0 adjudication**：独立复跑、current-hash binding、收敛阶和边界敏感性全部进入同一证据包。
4. **重做 audit**：把 detector 输出与被检测 claim 分离，消除 self-reference contamination。
5. **只选择一个窄子问题推进**：例如某个 Kerr Cauchy-horizon 正则性命题，或球对称标量模型中的已知机制复现。
6. **让数学合作者先 review 这些边界**：如果合作者认可 formulation 和证据契约，再考虑扩大 Astra 并行度。

## 14. 一句话版本

这个项目目前最像一张越来越精确的数学地图：我们已经知道哪些道路通向文献中的局部结果，哪些道路只是数值校准，哪些路标是伪影，哪些桥梁因 formulation hash 漂移而不能通行；真正穿越“开放问题”这条河，还需要一个被人类数学家接受的、类绑定且可证明的窄命题。

## 证据入口

- [Astra progress paper](./astra_progress_paper_20260913.md)
- [Early findings](./early_findings.md)
- [First audited-cycle evaluation](./evaluation_report.md)
- [Formulation taxonomy](./formulation_taxonomy.yaml)
- [Gate checklist](./gate_checklist.md)
- [Latest local controller report](../../../ai4math_runtime/math_controller_state/controller-report-20260913T224500.json)
