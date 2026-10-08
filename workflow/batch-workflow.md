# Batch Production Workflow

## Purpose

定义商品图片生产批次的标准流程。

---

# Batch Input

用户提供：

```
图片路径
工具路径
品类
```

---

# Batch Flow

```
图片路径

↓

读取品类规则

↓

扫描商品图片

↓

生成CSV数据

↓

人工InDesign数据合并

↓

导出图片

↓

OCR重命名

↓

文字清理

↓

生成批次包
```

---

# Batch Naming

格式：

```
日期_品类
```

示例：

```
2026-10-08_underwear
```

---

# Batch Output

每个批次包含：

```
csv/
indesign/
exported/
renamed/
cleaned/
report.md
```

---

# Status Tracking

建议记录：

```
scan: completed
csv: completed
indesign: waiting
ocr: pending
mask: pending
```
