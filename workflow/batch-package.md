# Batch Package Specification

## Purpose

定义一次商品图片生产任务的标准输出结构。

---

## Batch Naming

格式：

```
{日期}_{品类}
```

示例：

```
2026-10-08_underwear
```

---

## Output Structure

```
批次包
│
├── source
│   原始处理路径记录
│
├── csv
│   数据合并文件
│
├── indesign
│   ID相关文件记录
│
├── exported
│   InDesign导出图片
│
├── renamed
│   OCR识别并重命名后的图片
│
├── cleaned
│   去文字处理后的最终图片
│
└── report
    执行日志和异常记录
```

---

## Batch Principle

1. 每次任务生成独立批次。
2. 不修改原始图片。
3. 所有中间结果保留。
4. 失败步骤需要记录原因。
