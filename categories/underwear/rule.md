# 内裤图片命名与扫描规则

> 品类 ID：underwear。唯一机器匹配依据是以下 JSON；文字表格方便人工核对。

## 机器可读规则

~~~json
{
  "category": "underwear",
  "name": "内裤",
  "aliases": ["内裤", "underwear"],
  "slots": [
    {"label": "内裤正面", "suffix": "-1.png", "size": [4500, 4500], "required": true},
    {"label": "内裤背面", "suffix": "-2.png", "size": [4500, 4500], "required": true},
    {"label": "假模正面", "suffix": "-3.png", "size": [4500, 4500], "required": false},
    {"label": "假模背面", "suffix": "-4.png", "size": [4500, 4500], "required": false},
    {"label": "挂拍正面", "suffix": "-5.png", "size": [4500, 4500], "required": false},
    {"label": "裤口细节", "suffix": "-2.jpg", "size": [4500, 3000], "required": false},
    {"label": "裤边走线", "suffix": "-3.jpg", "size": [4500, 3000], "required": false},
    {"label": "裤腰细节", "suffix": "-4.jpg", "size": [4500, 3000], "required": false},
    {"label": "印花细节", "suffix": "-5.jpg", "size": [4500, 3000], "required": false},
    {"label": "其他细节", "suffix": null, "extension": ".jpg", "size": [4500, 3000], "required": false}
  ]
}
~~~

## 一、图片命名规范

| 图片类型 | 尾缀 | 尺寸 |
| --- | --- | --- |
| 内裤正面 PNG | `-1.png` | 4500 × 4500 px |
| 内裤背面 PNG | `-2.png` | 4500 × 4500 px |
| 假模正面 PNG | `-3.png` | 4500 × 4500 px |
| 假模背面 PNG | `-4.png` | 4500 × 4500 px |
| 挂拍正面 PNG | `-5.png` | 4500 × 4500 px |
| 未定义类型 | `-1.jpg` | 4500 × 3000 px |
| 裤口细节 JPG | `-2.jpg` | 4500 × 3000 px |
| 裤边走线 JPG | `-3.jpg` | 4500 × 3000 px |
| 裤腰细节 JPG | `-4.jpg` | 4500 × 3000 px |
| 印花细节 JPG | `-5.jpg` | 4500 × 3000 px |
| 其他细节 JPG | 无编号 | 4500 × 3000 px |

**注意：** 用户原版规范中 `-1.jpg` 对应图片类型为“/”，并没有给出确定名称。因此本版本不将其擅自指定为其他细节。出现 `-1.jpg` 时列入未匹配警告；无编号 JPG 才对应“其他细节”。

## 二、案例与目录

~~~text
0N2A0873/
└── 01_浅水蓝/
    ├── 0N2A0873-1.png  # 内裤正面
    ├── 0N2A0873-2.png  # 内裤背面
    ├── 0N2A0873-3.png  # 假模正面
    ├── 0N2A0873-4.png  # 假模背面
    ├── 0N2A0873-5.png  # 挂拍正面
    ├── IMG_8846-2.jpg  # 裤口细节
    ├── IMG_8848-3.jpg  # 裤边走线
    ├── IMG_8849-4.jpg  # 裤腰细节
    ├── IMG_8847-5.jpg  # 印花细节
    └── IMG_8850.jpg    # 其他细节
~~~

## 三、校验与安全策略

- 按 PNG/JPG 扩展名和末尾带连字符的编号匹配；不可跨品类解释编号。
- 同类型出现两张及以上时不选第一张，记录待确认。
- 无编号 JPG 若超过一张，不自动判断哪张是“其他细节”。
- 缺少图片可生成含空白字段的 CSV，但必选字段缺失必须报告；不虚称素材齐全。
- 尺寸不符只报告，不自动拉伸、裁切、覆写图片。
- 输出 CSV 图片列均带 `@`，例如 `@内裤正面`。
- 这里定义的是图片数据槽位和顺序，实际 ID 模板布局仍由设计师决定。
