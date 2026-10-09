# 商品图片自动拼图 Skill

一次输入商品图片路径，自动完成扫描、CSV 和 InDesign 数据导入/合并；设计师只需要在 InDesign 中微调、导出。随后再输入导出图片包路径，自动 OCR 重命名与去字。

## 运行流程

~~~text
第一次输入：商品图片路径
    ↓
Agent：识别品类，生成图片汇总.csv（UTF-16 LE）
    ↓
Agent：用对应 InDesign 模板自动 selectDataSource + mergeRecords
    ↓
自动保存：拼图_待人工调整.indd（已完成数据合并，可编辑）
    ↓
【人工】：只调整图片布局、检查、导出 JPG/PNG
    ↓
第二次输入：ID 导出图片包路径
    ↓
Agent：OCR 文字识别 → 重命名副本 → 固定白遮罩
    ↓
最终图片/
~~~

## 依赖与安装

- Windows 10/11，已安装并能够打开 Adobe InDesign 桌面版，系统注册 COM 对象 InDesign.Application。
- Python 环境。首阶段执行扫描 + InDesign 合并，后处理需要 Pillow、PaddleOCR / PaddlePaddle。
- scripts/ 下已内置：scan_product_images.py、ocr_rename_images.py、batch_add_white_mask.py、batch_runner.py、indesign_merge.py、indesign_merge.jsx。
- assets/indesign/ 下必须有两份真实的 .indd 二进制模板：内裤数据合并模板-最终版.indd、内衣套数据合并模板.indd。
- 注意：当前仓库可能只有模板的安装说明。使用前须把两份 .indd 真正放入对应目录，详见 assets/indesign/README.md。若是公司素材，请先确认公开仓库是否合适。

## 最简调用

用户说：
~~~text
调用商品拼图 Skill。
图片路径：F:/2026年秋冬/商品图片
帮我做拼图。
~~~

本地 Codex 自动执行：
~~~powershell
python scripts/batch_runner.py check --images "F:/2026年秋冬/商品图片"
python scripts/batch_runner.py prepare --images "F:/2026年秋冬/商品图片" --merge
~~~

如果品类不能唯一识别，Agent 只询问一次品类，再加 --category 内裤 或 --category 内衣套 重试；不再每次要求提供工具路径或模板路径。

固定数据合并字段：

内衣套：
~~~csv
货号,颜色,@上衣png,@下衣png,@领口,@袖口,@肩线,@裤腰
~~~

内裤：
~~~csv
货号,颜色,@正面png,@背面png,@印花,@裤口,@裤边,@裤腰
~~~

以上总计各 8 列，图片单元格指向本地原图片绝对路径。多条记录合并进一个新的可编辑 InDesign 文档。

**注意**：出现缺图、字段冲突、模板缺失、InDesign COM 不可用时，程序应停在问题状态。不能仅因为 CSV 成功就向用户声称“ID 已自动填入”。

## 人工调整后继续

人工在自动合并的 拼图_待人工调整.indd 里调整和导出，不需要自己去选择数据源。给 Agent 提供导出图片包路径后执行：

~~~powershell
python scripts/batch_runner.py resume --batch "日期品类批次目录" --exported "图片包目录"
~~~

成品只交付 最终图片/ 路径。后处理中原图与 ID 导出文件不被覆盖；OCR 和遮罩只操作副本。

## 测试范围

GitHub CI 可以测试 CSV、规则、Python 包装器、脚本生成和安全拦截；**不能在 Linux GitHub Actions 上真正启动 Windows InDesign COM**。首次生产需在你的 Windows + InDesign 本机做 1 个货号、1 个颜色的通路测试。
