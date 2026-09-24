# MathModel Flash 工作流

Flash 是速度优先的独立版本，适合 DeepSeek、Gemini、GLM 等 Flash 类高吞吐模型。它的交付目标是快速完成一份有真实实验、图表、数值结果和 Word 导出的基础长文草稿。

## 范围

- 只读取项目根目录的 `problem_files/`。
- 所有中间文件和交付物写入 `paper_output_flash/`。
- 默认 `plan.json` 使用 `delivery.mode = basic-long-paper` 和 `target_pages = 20`。
- 论文最低检查为 9000 个有效字符；最终报告还会估算页数并在低于目标时告警。
- 20 页是排版目标，不是用重复段落填充的承诺。结果不足时必须扩充真实的实验设计、验证、敏感性和局限讨论。

## 三个命令

```bash
python .claude/skills/mathmodel-flash/scripts/flash_preflight.py
python .claude/skills/mathmodel-flash/scripts/flash_run.py
python .claude/skills/mathmodel-flash/scripts/flash_finalize.py
```

预检会记录附件清单和哈希，并阻止与 Standard、Lite、Pro 或其他 Flash 安装混装。运行器会清除旧的 `results.json`，执行 `code/model.py`，记录脚本、计划、输入、结果、表格和图片的哈希。终检会核对结果问题覆盖、有限指标、正文数值、图片记录、占位文本、重复段落和 DOCX 重开内容。

## 论文结构

至少写出摘要、问题重述、假设与符号、数据处理、模型建立、求解算法、实验设计、每个问题的结果与检验、敏感性或局限、结论。每个子问题必须有唯一的 `Q*` 标题，正文须包含实际结果而不是只写方法名称。

Flash PASS 只表示快速稿的运行和文档完整性通过。它不等于 Standard 的证据链通过，也不等于 Pro 的独立复算、审稿和正式竞赛排版通过。
