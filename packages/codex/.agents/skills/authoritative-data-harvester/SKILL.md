---
name: authoritative-data-harvester
description: "MathModel Pro 公开来源研究与权威数据溯源。用于 P2 外部资料检索、关键声明交叉验证和 source_ledger.json。"
---

# Pro Authoritative Research

仅在检查点 1 新鲜批准后运行。自动研究只访问公开资源；登录、付费、私有数据、
受限 API 或额外授权材料必须先取得用户明确授权。不要用搜索摘要代替原始页面，
不要把无法访问的 URL 标为已验证。

优先政府、国际组织、官方数据库、标准机构、原始论文和数据发布者。关键外部数据
尽量由两个独立权威发布者交叉验证；若客观上只有单一权威源，记录例外理由和风险。

用总入口的 `pro_capture_source.py --url <URL> --source-id <S1>` 将公开响应保存到
`paper_output_pro/research/`，保留检索回执、原文件和哈希。每个来源写入
`paper_output_pro/source_ledger.json`，包含 URL、标题、发布者、UTC 访问时间、
内容 SHA-256、公开访问状态、用途和论文 claim ID。每个关键 claim 记录来源 ID、
是否需要双源验证以及差异处置。

不得无来源填写关键数值，不得把用户私有数据标成公开来源，不得引用失效或未实际
打开的链接。运行 `scripts/validate_source_ledger.py`，失败则不进入模型竞赛。
