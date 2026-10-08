# 批次生产工作流

## 输入
- 图片路径：单个货号文件夹，或包含多个货号文件夹的父目录。
- 工具路径：包含指定三个 Python 工具的本地目录。
- 品类：内裤 / 内衣套，以及新增的规则 ID 或 alias。

## 状态机

~~~text
check（只检查）
  ↓
prepare（源图扫描、生成UTF-16 LE CSV、创建批次）
  ├─ needs_mapping（有歧义）→ 人工确认字段 → prepare --overrides（新批次）
  └─ waiting_indesign（数据就绪）
        ↓
      人工 InDesign 数据合并、检查排版、导出图片
        ↓
resume（OCR 副本重命名、固定白遮罩）
        ├─ completed
        └─ completed_with_warnings（查看 report/report.md）
~~~

首次运行只到 `waiting_indesign`，必须等用户真正导出图片以后才允许续跑。

## 不覆盖原则

不移动、不更改源目录素材；不覆盖已有日期_品类批次；重命名只操作导出图片的副本。已存在的 ID 导出文件如内容相同可安全续跑，不同则报错。

## 记录

`batch.json`：时间、品类、输入、工具、记录数量、阶段、警告。
`report/report.md`：缺项、重复、尺寸不符、未匹配文件、后处理问题。
`report/overrides-needed.json`：需确认字段以及候选文件列表。

## 完成条件

- prepare 结束不等于拼图完成；只有 ID 人工输出并成功后处理才有最终图片。
- 不能自动确认用户尚未提供的 ID 模板、背面位置和遮罩位置。
