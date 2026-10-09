# 简化批次输出规范

用户输入图片路径、工具路径、品类，Skill 根据本机日期创建不同的批次目录。运行时目录名使用品类英文 ID：`YYYY-MM-DD_underwear` 或 `YYYY-MM-DD_underwear-set`。

**Agent 完成表格和 InDesign 自动填入后**，交付：

~~~text
2026-10-08_underwear/
├── 图片汇总.csv
└── 待人工调图.indd
~~~

含歧义则为 `图片汇总_待确认.csv`，尚不能导入 ID。

**用户手工调图、导出并提供导出目录后**，第三和第四步自动执行，得到：

~~~text
2026-10-08_underwear/
├── 图片汇总.csv
└── 最终图片/
    ├── 浅水蓝.png
    └── …
~~~

程序还会创建隐藏的 `.skill/` 文件夹，保存 batch.json、report.md、overrides-needed.json（按需）、ID导出副本和OCR重命名副本。**这些不是用户要直接操作的交付物**，不要在普通回复里列出详细目录树。

原始图片不复制、不修改。已存在同名批次时自动追加序号，防止覆盖。
