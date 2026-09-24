# Flash 启动提示词

将下列提示词发送给已经安装 Flash 包的 Agent：

```text
请使用 $mathmodel-flash 完成这道数学建模题。赛题和附件在 problem_files/。

这是速度优先的基础长文版本：
1. 先运行 flash_preflight.py，确认没有混装并记录全部输入哈希；
2. 为每个子问题建立一个可解释、可快速运行的模型，写入 paper_output_flash/plan.json；
3. 写一个真正读取附件并运行计算的 paper_output_flash/code/model.py，生成 results.json、CSV 和图表；
4. 运行 flash_run.py，失败就修复后重跑，不要手写结果；
5. 生成约 18-22 页目标的完整 paper.md，包含实验、数值、验证、局限和结论，不用重复段落凑页数；
6. 运行 flash_finalize.py，只有 flash_report.json 为 PASS 才交付 paper.docx。

所有产物只写入 paper_output_flash/。不要读取 Standard、Lite、Pro 或其他旧输出，不要把短摘要冒充 20 页论文。明确说明 Flash 草稿仍需人工和更高档版本复核。
```
