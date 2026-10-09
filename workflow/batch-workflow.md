# 商品拼图两次输入流程

## 第一次输入：商品图片路径

自动执行 check → prepare --merge。
1. 按品类规则生成 UTF-16 LE 图片汇总.csv。
2. 自动用内置 InDesign 模板打开 Adobe InDesign 桌面版。
3. JSX 使用 selectDataSource() 导入 CSV、mergeRecords() 合并全部记录。
4. 另存新可编辑文档 拼图_待人工调整.indd，状态 waiting_manual_export。
5. Agent 告知用户可以调整并导出，**不是让用户手动导入 CSV**。

失败处理：
- needs_mapping：同字段冲突，等待映射。
- needs_images：必选图片缺失，不执行合并。
- needs_template：.indd 缺失或未通过校验，不执行合并。
- indesign_merge_failed：PowerShell COM/Adobe 合并未成功，保留 CSV 和错误日志。
不能把“CSV 已生成”说成“ID 已填入”。

## 唯一人工环节

设计师打开自动合并文档，调整版式并导出图片包。既不手动选数据源，也不手动创建合并文档。

## 第二次输入：ID 导出图片包路径

Agent 用第一次生成的批次目录运行 resume：
1. OCR 识别并重命名导出图副本。
2. 在固定文字区加白色遮罩去字。
3. 仅给出最终图片目录、成功与异常数量。

## 安全原则

不覆盖源素材、原始 ID 模板、旧批次或人工导出的源文件。
模板缺失、脚本失败和图片缺失不静默放行。
GitHub Actions 验证的是自动化逻辑，Windows InDesign GUI 需本机真实测试。
