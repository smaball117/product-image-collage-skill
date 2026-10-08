# 日期 + 品类批次包规范

命名：`YYYY-MM-DD_{category}`，如 `2026-10-08_underwear`。同一天多次执行按序添加 `-02`、`-03`，禁止覆盖。

默认输出位置：输入图片路径的父目录下 `product-collage-output/`；亦可在 `prepare` 阶段使用 `--output-root`。

~~~text
2026-10-08_underwear/
├── batch.json                 # 生产状态、源路径和工具路径
├── source/
│   └── source-path.txt        # 源图片位置记录，不复制 4500px 原始图
├── csv/
│   ├── data_merge_utf16.csv   # ID 用，UTF-16 LE + BOM
│   └── data_merge_utf8.csv    # 核对用
├── indesign/
│   └── IMPORT.txt             # 人工 ID 操作交接说明
├── exported/                  # 导出的原始拼图图片副本
├── renamed/                   # OCR 后命名的副本
├── cleaned/                   # 加固定白色遮罩后的最终图片
└── report/
    ├── report.md
    └── overrides-needed.json  # 仅有无编号歧义或同字段冲突时生成
~~~

- **图像列均以 @ 开头**，文字列货号、颜色不加 @。
- `needs_mapping` 说明无法确定图像对应关系；不能未经确认直接操作 ID。
- `completed_with_warnings` 并非完全成功；根据报告处理个别失败图。
