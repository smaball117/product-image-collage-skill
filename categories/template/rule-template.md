# 品类规则模板

> 每个品类一个目录 `categories/{category-id}/rule.md`。首个 `~~~json` 块由 `scripts/batch_runner.py` 读取；必须保证 JSON 可解析、label 唯一、suffix 不冲突。

## 机器可读规则（复制后修改）

~~~json
{
  "category": "category-id",
  "name": "品类中文名",
  "aliases": ["中文名", "category-id"],
  "slots": [
    {"label": "主体正面", "suffix": "-1.png", "size": [4500, 4500], "required": true},
    {"label": "主体背面", "suffix": "-2.png", "size": [4500, 4500], "required": false},
    {"label": "细节特写", "suffix": "-1.jpg", "size": [4500, 3000], "required": false}
  ]
}
~~~

## 填写规则

- `suffix` 必须是图片文件名结尾的完整编号加扩展名，如 `-1.png`、`-2.jpg`。
- `suffix: null` 表示**无编号**图片，并为该项填写 `extension`（仅 `.png` 或 `.jpg`）。如果同一格式下有多个无编号槽位，程序会留下待映射而不会猜图。
- `size` 为期望像素宽高，只校验，不裁切、重采样或更改原图。
- `required` 指缺失是否应记录在“必选缺项”报告中。不要在缺少依据时擅自把选填改成必选。
- 每种图片类型的 `label` 唯一，生成 CSV 时加 `@` 作为图片字段列标题；`货号`、`颜色` 不加 `@`。
- 正文说明可写命名案例、目录结构、图片排序及例外事项，但**机器识别以 JSON 为准**。
- 未定义编号不要擅自绑定到类型；出现时记为“未匹配文件”。

## 新增步骤

1. 在 `categories/` 建立新的英文品类 ID 目录。
2. 复制该模板到 `categories/{category-id}/rule.md` 并替换占位值。
3. 检查后执行 `python scripts/batch_runner.py check --category "中文名" --tools "工具路径"`。
4. 用一套真实货号/颜色文件夹做 `prepare` 试运行并检查字段与图片是否对应。
