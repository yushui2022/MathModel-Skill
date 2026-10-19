# Standard 通用包迁移验收

## 范围与基线

- 开发分支：`unified-skills`；版本：`2.4.0-dev.2`。
- 运行完整性基线：`47423bf`，提交前通过 126 项单元/集成测试及原有 42 项工作流回归。
- 原 Claude canonical 迁入 `skills/`，删除两个镜像 payload 和三个旧平台 ZIP；十个 Skill 和 S0-S8 业务流程保留。
- Lite、Flash、Pro、LaTeX 分支及既有 B 题示例未修改；不创建 Tag/Release，不调用付费模型。

## 本地验证

实际环境为 Windows、Python 3.11；安装器测试通过 `python -S` 验证不依赖第三方库。

| 检查 | 本地结果 |
|---|---|
| `python -m unittest discover -s tests -p 'test_*.py'` | 150 项运行，149 项通过，1 项因 Windows 符号链接创建权限跳过 |
| 新增主目录保护后的 `python -S tests/test_installation.py` | 22 项运行，21 项通过，1 项同样因符号链接创建权限跳过 |
| `python -u tests/run_tests.py` | 原有 42 项回归全部通过，平台测试改为实际安装通用 ZIP |
| Skill Creator 校验 | 十个 Skill 全部通过 |
| `scripts/check_skills.py` | 单一 payload、版本、所需文件、内部引用及硬编码路径检查通过 |
| Python 编译、`pip check`、工作流 YAML 解析 | 通过 |
| LibreOffice | 原回归与从通用 ZIP 安装后的 DOCX/PDF 渲染测试通过；最终单元测试设置 `MATHMODEL_REQUIRE_RENDER=1` |

安装覆盖首次、重复、只读检查、手动安装、同主版本托管升级、旧包冲突、用户文件改动、全局目录拒绝、五种根目录混装、Flash 识别、清单篡改、并发、正常异常回滚和进程硬中断恢复。
普通符号链接测试因本机权限跳过，但 Windows 目录联接拒绝测试通过。恢复备份被用户修改时，恢复停止且文件快照保持不变。

三个目标位置均从 ZIP 解压后调用同一个安装器；逐文件比较安装内容，并确认原项目配置、附件、其他 Skill 和旧论文产物未变化。
预测与整数优化两个合成案例使用安装后的代码执行真实 runner、S6 和 S7 数值审计。Quickstart 从不同工作目录运行，草稿仍只写赛题的 quickstart 目录。已有预检 PASS 后修改已安装 Skill，也会被后续 workflow guard 拦截。

## 分发与维护

只生成 `dist/MathModel-Skill-Standard.zip` 与 `dist/SHA256SUMS.txt`。固定 ZIP 元数据、使用 ZIP_STORED、显式文本类型转 LF；本地三份构建的 SHA-256 一致，发布包另行逐文件及整包验证。

安装器复用包清单和 Edition marker，安装记录只包含自身文件。`--upgrade` 不接管无记录安装，不跨 edition/主版本，不降级，不重新签署已有论文证据。
源文件新增或删除后，应同步入口 Edition marker 的 `required_files` 清单，再运行 `check_skills.py` 和打包验证；普通内容编辑不需要更改该文件列表。

## 尚未验证

- GitHub Actions 尚未执行本次变更。已配置 Windows/Ubuntu/macOS × Python 3.11/3.12 的标准库安装及确定性构建矩阵；跨系统字节一致性需远端 CI 确认。
- 未在三个宿主的真实界面中验证自动发现、自动调用或菜单刷新；目录和脚本测试不等于宿主 UI 验收。
- 合成测试和短文渲染不是完整真实赛题、20 页终稿或获奖质量验证。
- 文件哈希是完整性检查，不是可信发布者签名，也不是能抵御恶意本地进程的安全沙箱。
