# Standard Skill 元数据与评估集验收

- 日期：2026-10-21。
- 范围：`standard` 分支，版本 `2.4.0-dev.4`，基线 `358fd6c`。
- 不修改其他版本分支、既有 B 题示例；不创建 Tag/Release；不调用付费模型。

## 改动内容

1. 十个 Skill 的 `description` 重写为中文第三人称，统一为「做什么。当…时使用。」，删除 `Invoke when` 元语言，并把落点路径、内部结构等实现细节移回正文。
2. 十个 Skill 新增 `compatibility`，把 Python 3.11–3.12、LibreOffice、可选 scipy 与图表依赖写进元数据。
3. 补齐 4 处「一层深」引用缺口：`context-memory-keeper` 两处、`model-code-and-result-generator` 一处、`modeling-paper-rubric-and-model-selector` 一处；四个超过 100 行的参考文件补目录。
4. `agents/openai.yaml` 从 2/10 补到 10/10，`display_name`、`short_description`、`default_prompt` 口径统一；新文件登记进 `MATHMODEL_EDITION.json` 的 `required_files`（66 → 74）。
5. 新增 `evals/`：20 条触发用例、三个关键 Skill 的产出层 `evals.json`、以及只依赖标准库的 `scripts/check_skill_triggers.py`。
6. `problem-doc-model-selector` 的示例路径由仅 Windows 的 `c:\path\to\赛题.pdf` 改为 `problem_files/赛题.pdf`。
7. 版本推进到 `2.4.0-dev.4`，重建确定性发布包；安装器测试改为从 `VERSION` 推导升级目标版本，不再硬编码下一个版本号。

## 本机验证

Windows、Python 3.11.1：

| 检查 | 结果 |
|---|---|
| `scripts/check_skills.py` | 通过（载荷、版本、内部引用） |
| `scripts/build_release_packages.py --verify` | 通过，`2.4.0-dev.4`，90 个文件 / 817.8 KB |
| `tests/run_tests.py` | 原有 42 项工作流回归全部通过 |
| `python -S tests/test_installation.py` | 24 项，22 通过，2 项平台相关跳过 |
| `tests/test_installed_workflow.py` | 3 项通过 |
| `scripts/check_skill_triggers.py --strict` | 20/20，退出码 0 |
| `skills/*/agents/openai.yaml` | 10 个全部可被 YAML 解析 |
| `evals/**.json` | 4 个均可解析 |

## 触发测试与它的边界

同一组 20 条真实口吻提示词、同一套匹配器，对新旧描述做 A/B：

| 描述版本 | top-1 命中 |
|---|---|
| 修改前（含 `Invoke when`） | 9 / 20 |
| 修改后 | 19 / 20 |

唯一未命中为「把结果画成能放进论文的图，图注也写上」，被判定给代码生成器；在数据清洗 Skill 描述中补入「图注」后重跑为 20/20。旧描述最典型的三处误判是请求续跑流程、章节局部重写和记录决策时分别命中数据抓取、质量审计和记忆 Skill。

**这不是模型路由实测。** `check_skill_triggers.py` 使用字符二元组与 ASCII 词的 TF-IDF 余弦相似度，属于词面代理，只适合发现「两个 Skill 借用了同一套措辞」这类冲突，不能证明真实宿主下的发现准确率。要得到后者的证据，需要接真实模型执行 `evals/<skill>/evals.json` 的带 Skill / 不带 Skill 双跑基线，本轮未做。

## 远端 CI

- 提交 `b116151` 的 [run 39548955201](https://github.com/yushui2022/MathModel-Skill/actions/runs/39548955201)：13 个任务全部通过，包含首次执行的 macOS 核心回归（Python 3.11 用时 149 秒、3.12 用时 108 秒）、Ubuntu/Windows 核心回归、LibreOffice 强制渲染与三平台安装打包。
- 提交 `3039d55` 的 [run 39551731559](https://github.com/yushui2022/MathModel-Skill/actions/runs/39551731559)：13 个任务全部通过，覆盖本轮 `agents/openai.yaml` 与清单变更。

核心测试矩阵此前只有 Ubuntu 与 Windows；macOS 仅在安装打包任务里执行 `test_installation.py`。本次把 macOS 加入核心矩阵后，平台相关的路径处理会在回归阶段暴露，而不是等到某个版本分支单独踩坑。

## 未做与理由

### Skill 重命名

十个 Skill 名称长度为 19–40 字符，均在规范的 64 字符上限内；`modeling-paper-rubric-and-model-selector`（40）最接近需要收敛的程度，但本轮不重命名。

原因是安装器当前无法安全承载改名：`installation.py` 的 `apply_install` 只对 `SKILLS` 集合内的目录执行 `os.replace`，不会删除新载荷中已不再存在的托管目录；`scan_installations` 按目录名与 edition marker 扫描。改名后老项目会留下孤儿 Skill 目录，宿主可能同时发现新旧两套 Skill。要安全改名，需要先实现「清理已移除的托管目录 + 失败回滚」并补对应测试，属于安装器新特性，超出元数据整理的范围。

### 其他

- 未执行真实赛题论文质量评测；既有 B 题示例未重新生成。
- Trae 的 GUI 发现仍未验收。
- `compatibility` 是元数据声明，当前宿主不强制校验；缺依赖时仍需靠预检脚本拦截。
