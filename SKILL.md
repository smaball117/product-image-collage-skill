# Product Image Collage Skill

## Overview

商品图片自动拼图生产 Skill。

目标：根据用户提供的商品路径和品类，自动读取对应品类规则，识别商品图片，完成图片整理、数据生成、辅助处理，并输出拼图所需素材。

本 Skill 采用「主 Skill 调度 + 品类规则文件」架构。

---

# User Input

用户调用格式：

```
调用 product-image-collage skill

产品路径：xxx

品类：内裤 / 内衣套 / 其他

帮我做拼图
```

---

# Core Workflow

## Step 1：确认输入信息

必须获取：

- 产品图片路径
- 产品品类

禁止根据图片内容猜测品类。

---

## Step 2：加载品类规则

根据用户提供的品类，读取：

```
categories/{category}/rule.md
```

规则文件负责定义：

- 图片命名规则
- 图片类型映射
- 文件夹结构
- 拼图顺序
- 异常处理

不同品类之间禁止共享编号解释。

例如：

- 内裤 `-1.png` 与内衣套 `-1.png` 含义不同。

必须以当前品类 rule.md 为唯一判断依据。

---

## Step 3：扫描商品图片

调用图片扫描工具：

目标：

- 读取货号文件夹
- 读取颜色文件夹
- 根据规则匹配图片
- 生成图片映射数据

输出检查报告：

```
货号：xxx
颜色：xxx

已找到：
✓ 正面图
✓ 背面图

缺少：
× 细节图
```

---

## Step 4：生成拼图数据

根据品类规则生成：

- 图片排列顺序
- 图片组合关系
- 拼图素材列表

---

## Step 5：人工节点

以下步骤保留人工操作：

- InDesign 数据合并
- 页面位置调整
- 最终导出确认

Skill 不自动模拟设计软件点击操作。

---

## Step 6：后处理

支持：

- OCR 图片文字识别
- 图片自动重命名
- 图片文字区域清理
- 输出整理

---

# Directory Structure

```
product-image-collage-skill
│
├── SKILL.md
│
├── categories
│   ├── template
│   │   └── rule-template.md
│   ├── underwear
│   │   └── rule.md
│   └── underwear-set
│       └── rule.md
│
├── scripts
│
├── templates
│
└── config
```

---

# Hard Rules

1. 不允许跨品类解释图片编号。
2. 不允许修改原始图片，所有处理输出到新目录。
3. 所有异常必须生成报告。
4. 新增品类必须新增独立 rule.md。
