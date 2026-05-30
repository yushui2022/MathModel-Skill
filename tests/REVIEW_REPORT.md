# Round 1 硬化测试报告

> 提交给 Codex 审议。不要 commit，等 Codex review。

## 1. 变更范围（三套同步）

| 文件 | 改动 | 说明 |
|---|---|---|
| `paper-workflow-orchestrator/scripts/preflight_check.py` | **新增** | 输入资产健康预检，按文件类型触发依赖检查；ASCII stdout；写 `paper_output/preflight_report.json` |
| `paper-workflow-orchestrator/SKILL.md` | 顶部插入"启动门"和"Quickstart 用途说明"两节 | 让 Agent 第一步先跑 preflight；明确 quickstart 仅用于安装验证 |
| `paper-workflow-orchestrator/scripts/quickstart_run.py` | Step-10 重定向 | quickstart 草稿写到 `paper_output/quickstart/quickstart_draft.docx`，**不再覆盖** `final_paper.docx` |
| `paper-workflow-orchestrator/scripts/run_all.py` | 文案重写（修复 GBK mojibake） | 指向 preflight + 总控 SKILL.md；仍只打印迁移提示、不执行流程 |
| `paper-formal-writer/scripts/format_formal_docx.py` | `main()` 加 argparse + `--allow-draft` + 证据门禁自检 | 无 `evidence_gate_report.json` 或 `status != PASS` → 默认 exit=2 阻塞；`--allow-draft` 走草稿路径，写 `final_paper_draft.docx` + `format_draft_report.md`，不触碰正式产物 |

三套差异仅在路径前缀（`.claude/...` vs `skills/...` vs `.trae/skills/...`），脚本主体逻辑完全一致。

## 2. 测试场景与结果

测试沙箱：`tests/sandbox/scenario_*/`，每个场景独立 cwd 跑预检。

### 2.1 preflight_check.py 5 场景

| 场景 | 内容 | 预期 | 实际 |
|---|---|---|---|
| `scenario_1_empty` | `problem_files/` 存在但为空 | FAIL + 提示空目录 | ✅ FAIL, exit=1，错误："problem_files/ 为空" |
| `scenario_2_only_doc` | 只放一个 `题目.doc` | FAIL + 提示无可解析文档 | ✅ FAIL, exit=1，错误："没有可解析的题面文档" |
| `scenario_3_broken_xlsx` | 题面 .md + 伪造的 `broken.xlsx`（非 zip） | FAIL + xlsx 打开失败 | ✅ FAIL, exit=1，错误："BadZipFile: File is not a zip file" |
| `scenario_4_suspicious_template` | 题面 .txt + `result1.xlsx`（合法 xlsx 但文件名疑似结果模板） | PASS + 警告结果模板 | ✅ PASS, exit=0，warning："文件名疑似结果模板（含 result/结果/submit/提交），不可当作原始数据使用" |
| `scenario_5_stale_output` | 题面 .md + 已存在的 `paper_output/final_paper.docx` | PASS + 警告陈旧产物 | ✅ PASS, exit=0，warning："检测到旧的 final_paper.docx" |

### 2.2 format_formal_docx.py 证据门禁

在 `scenario_4` 上叠加 `final_paper_source.md`，依次：

| 子测试 | 预期 | 实际 |
|---|---|---|
| A. 无 `evidence_gate_report.json`，无 `--allow-draft` | 阻塞 exit=2，不写任何 docx | ✅ exit=2，目录里只有 source.md + preflight_report.json |
| B. 无报告 + `--allow-draft` | 写 `final_paper_draft.docx` + `format_draft_report.md`，不写 `final_paper.docx` | ✅ 只有 draft 系列文件出现 |
| C. 写入 `status:PASS` 报告，无 `--allow-draft` | 正常生成 `final_paper.docx` + `format_check_report.md`，draft 文件保留 | ✅ 正式文件出现，draft 未被清掉（独立路径） |
| D. 写入 `status:FAIL` 报告，无 `--allow-draft` | 阻塞 exit=2，错误指明 status=FAIL | ✅ exit=2，原因："证据门禁状态为 \`FAIL\`" |

## 3. 设计要点（响应 Codex Round-0 8 点 + Round-1 10 点）

- **预检按文件类型触发依赖**：只有 `problem_files/` 里出现 .pdf 才检查 pypdf；出现 .xlsx 才检查 openpyxl。避免无关依赖缺失阻断流程。
- **.doc 边角处理**：列为 candidate 但 `extractable=False`；如果是唯一一个题面 → FAIL（场景 2 验证）。
- **PDF 文本量阈值**：先抽前 5 页；若 0 字符且总页数 > 5，扩到 20 页；最终若 < 200 字符给 warning 而非 fail。
- **可疑文件名识别**：`result*` / `结果*` / `submit*` / `提交*` 的 xlsx/xls/csv 仅警告，不阻断（场景 4）。
- **陈旧 final_paper.docx**：仅警告（场景 5），让 Agent 自己决定归档还是删除。
- **ASCII-only stdout**：所有 print 不含 emoji，避免 Windows GBK 终端崩溃。
- **Quickstart 不再污染正式产物**：草稿落到 `paper_output/quickstart/quickstart_draft.docx`。
- **格式门禁默认阻塞**：必须显式 `--allow-draft` 才进入草稿模式；草稿 / 正式输出路径完全分离，无相互覆盖风险。

## 4. 不在本轮范围

- `quality-assurance-auditor/scripts/evidence_gate.py` 本身未改（已具备 `official/quickstart` 模式）。
- `paper-formal-writer/scripts/check_paper_format.py` 字数 / 标题 / 引用门禁未动。
- README.md 未动（按用户要求"先不改 readme"）。
- 未做 `git add` / `git commit` / `git push`。

## 5. 复现命令

沙箱本身被 `tests/.gitignore` 排除；用 `tests/setup_sandbox.py` 一键重建：

```bash
# 在仓库根目录
python tests/setup_sandbox.py

# 跑 5 个常规场景的预检
for S in tests/sandbox/scenario_1_empty tests/sandbox/scenario_2_only_doc tests/sandbox/scenario_3_broken_xlsx tests/sandbox/scenario_4_suspicious_template tests/sandbox/scenario_5_stale_output; do
  (cd "$S" && python ../../../packages/claude/.claude/skills/paper-workflow-orchestrator/scripts/preflight_check.py)
done

# 场景 6：缺 pypdf 依赖（用 runtime import-blocker 模拟，不真的卸载）
cd tests/sandbox/scenario_6_no_pypdf
PREFLIGHT="$(pwd)/../../../packages/claude/.claude/skills/paper-workflow-orchestrator/scripts/preflight_check.py" python -c "
import os, sys, runpy
class Blocker:
    def find_module(self, name, path=None):
        if name == 'pypdf' or name.startswith('pypdf.'):
            return self
    def load_module(self, name):
        raise ImportError(f'blocked: {name}')
sys.meta_path.insert(0, Blocker())
sys.argv = ['preflight_check.py']
try:
    runpy.run_path(os.environ['PREFLIGHT'], run_name='__main__')
except SystemExit as e:
    print(f'EXIT={e.code}')
"

# 跑格式门禁（scenario_4）
cd tests/sandbox/scenario_4_suspicious_template
python ../../../packages/claude/.claude/skills/paper-formal-writer/scripts/format_formal_docx.py                # expect exit 2
python ../../../packages/claude/.claude/skills/paper-formal-writer/scripts/format_formal_docx.py --allow-draft  # expect draft
```

## 6. Round-1.5 后续修订（响应 Codex 审议）

| 问题 | 修法 |
|---|---|
| P2#1 frontmatter 太长，不利于自动入口命中 | 三套 `SKILL.md` 改短为：`"MathModel Skill 总入口。触发词：数学建模、生成论文、分析赛题、CUMCM、MathorCup、华数杯、美赛、ICM、MathModel。任何数学建模任务先读本 skill 再路由子 skill。"` |
| P2#2 quickstart 残留正式命名中间稿 | quickstart 加 Step-11：把 `paper_output/final_paper.md` → `paper_output/quickstart/quickstart_draft.md`，`paper_output/final_paper_direct.docx` → `paper_output/quickstart/quickstart_direct.docx`（原 quickstart_draft.docx Word 仍由 Step-10 直接写到 quickstart 目录）。验证完成后 `paper_output/` 顶层不再残留正式命名稿。 |
| P3#3 沙箱产物入库 | 删掉 `tests/sandbox/`，新增 `tests/.gitignore`（忽略整个 sandbox/）+ `tests/setup_sandbox.py`（一键重建，可复现）。 |
| P3#4 缺 pypdf 场景未覆盖 | 在 `setup_sandbox.py` 加 scenario_6_no_pypdf：写入合法 PDF；跑测时用 `sys.meta_path` Blocker 拦截 `import pypdf`。复跑结果：`[PRECHECK FAIL]`，错误同时报"依赖缺失：pypdf"和"没有可解析的题面文档"，exit=1，符合预期。 |
