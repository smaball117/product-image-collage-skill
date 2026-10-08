# Product Image Collage Skill

## Overview

商品图片自动拼图生产 Skill。

目标：根据用户提供的商品路径、品类和工具路径，自动读取对应品类规则，调用本地 Python 工具完成商品图片整理流程。

本 Skill 采用：

「主 Skill 调度 + 品类规则 + 外部工具路径配置」架构。

---

# User Input

用户调用格式：

```
调用 product-image-collage skill

产品路径：xxx

品类：内裤 / 内衣套 / 其他

工具路径：xxx

帮我做拼图
```

---

# Tool Configuration

用户提供工具目录后，读取其中的 Python 工具：

```
scan_product_images.py
ocr_rename_images.py
batch_add_white_mask.py
```

工具不要求存放在 GitHub Skill 仓库中。

Skill 只负责调度，不复制工具文件。

---

# Core Workflow

## Step 1：确认输入信息

必须获取：

- 产品图片路径
- 产品品类
- Python 工具路径

禁止根据图片内容猜测品类。

---

## Step 2：加载品类规则

根据用户提供的品类读取：

```
categories/{category}/rule.md
```

规则文件负责定义：

- 图片命名规则
- 图片类型映射
- 文件夹结构
- 拼图顺序
- 异常处理

不同品类禁止共享编号解释。

---

## Step 3：调用图片扫描工具

调用：

```
scan_product_images.py
```

输入：

- 产品图片路径

输出：

- 图片分类结果
- CSV数据

---

## Step 4：人工 InDesign 节点

保留人工操作：

- 导入 CSV
- 数据合并
- 调整位置
- 导出图片

Skill 不模拟设计软件操作。

---

## Step 5：OCR 后处理

调用：

```
ocr_rename_images.py
```

作用：

- OCR识别图片文字
- 根据识别结果重命名图片

---

## Step 6：图片清理

调用：

```
batch_add_white_mask.py
```

作用：

- 删除导出图片中的文字区域
- 输出清理后的图片

---

# Hard Rules

1. 不允许跨品类解释图片编号。
2. 不修改原始图片。
3. 所有处理输出到新目录。
4. 所有异常生成报告。
5. 新增品类必须新增独立 rule.md。
