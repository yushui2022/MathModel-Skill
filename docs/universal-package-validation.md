# LaTeX 通用包迁移验收

日期：2026-10-19。版本：`2.0.0-latex.1`。本机：Windows、Python 3.11.1。

## 变更边界

- 唯一源码：仓库根 `skills/`；唯一安装包：`MathModel-Skill-LaTeX.zip`。
- 删除 Git 中的旧平台 payload、旧平台 ZIP、平台同步脚本。保留原 Skill 名称、业务流程、证据与论文门禁。
- 安装器只选择项目内目标位置，不写全局目录，不覆盖用户根指令、依赖、其他 Skill、附件或结果。
- Standard 分支与所有现有赛题示例未改动。没有修改历史 Release，也没有创建新 Tag 或 Release。

## 本地验证

- 安装器：27 项测试，25 通过、2 跳过（macOS 专用案例与无权限创建的符号链接）。Windows 目录联接拦截实际通过。
- 覆盖首次、只读检查、重复、手动使用、显式升级、拒绝降级、用户改动、中文/空格路径、锁竞争、异常回滚、硬中断恢复、五种旧/新路径、混装及同目录残缺异版。
- 对根配置、其他 Skill、原始附件、既有结果进行前后字节比较。
- 真实 ZIP 安装到 Codex、Claude、Trae 目录；安装器使用 `python -S` 测试，证明无需第三方依赖。
- 导出完整性测试 17 项、证据门禁 10 项、预览证据 4 项、旧流程 5 组均通过。
- 三种安装位置均完成预检、实际证据门禁和 TeX 源文件导出；修改证据后正式导出被阻止。
- 本机未安装 XeLaTeX。正向编译回执测试使用 mocks；安装集成仅检查源文件生成并确认没有冒充成功 PDF。
- Skill Creator 校验、内部引用检查、Python 编译通过。
- 本地两次独立打包与 `dist/` 当前 ZIP、SHA256SUMS.txt 字节一致；ZIP_STORED、排序、固定时间与权限、文本 LF。
- 现有测试环境 `pip check` 通过；没有调用付费模型或联网下载模型。

## 未覆盖与使用边界

- 已配置 Windows/Ubuntu/macOS × Python 3.11/3.12 安装器与打包 CI；这不是远端矩阵已经执行成功的声明。本地只执行 Windows/Python 3.11.1。
- 本轮没有真实宿主界面自动发现验收，尤其不能把目录安装成功称为 Trae 多代理或复杂工具能力认证。
- 未进行新模型的真实竞赛长文前向验收，不承诺论文质量、页数或获奖。
- 无安装记录的旧包不自动迁移，手动安装不自动纳入托管；用户须先备份和解决冲突。
- 新通用安装器不是任意建模代码的执行沙箱。升级前停止正在运行的建模任务，升级后重新预检并复核原有门禁。

## 复查命令

```bash
python scripts/check_skills.py
python -S tests/test_installation.py
python tests/test_installed_workflow.py
python -S scripts/build_release_packages.py --verify
```
