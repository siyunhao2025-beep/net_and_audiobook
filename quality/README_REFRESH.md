# README 升级验证 · 2026-10-31

## 已完成

- 从GitHub检索、读取并安装beautify-github-readme、crafting-effective-readmes和joke-engineering；固定来源版本、校验下载文件blob、保留许可与必要资源，保存后核验安装状态。来源见[设计记录](../docs/README_DESIGN.md)。
- 增加3张原创可编辑SVG：封面、制作流程、五段朗读；2张1440×960原创demo真实截图。截图通过实际应用获取，播放器在真实开始播放后暂停截取，避免录入加载中间状态。
- 维护现有使用说明，新增Bash/PowerShell指南、可复现SVG生成与截图工具。声线、英语语速、音频顺序和播放器实现未改动。
- 公开导出扫描新增显式README PNG开关，只允许assets/readme中格式、尺寸、体积与元数据均通过的PNG；默认仍拒绝未经审查的二进制。

## 实际检查

| 检查 | 结果 |
|---|---|
| 已安装README skill自带audit_readme.py | 5张本地图片，引用、alt和SVG基础检查通过 |
| 自带GIF工具CLI | help正常；本次没有创建动画，未声称GIF渲染全链路通过 |
| 本仓库check_readme.py | 本地链接/锚点、5张图片、SVG兼容性与PNG解码/元数据检查通过 |
| Windows契约测试 | 13/13通过，含真实Windows文件句柄和新增图片白名单检查 |
| Linux契约测试 | 13项运行，12通过；真实Windows句柄项按环境跳过 |
| GitHub风格本地浏览器预览 | 1100px视窗（约900px内容列）/390px × 明/暗4格均通过 |
| 预览行为 | 无页面横向溢出，5张本地图片加载、3个折叠块、显式锚点正常，无JS异常 |
| 视觉检查 | 检视桌面/手机、真实播放器正常暂停状态、SVG文字与布局；核心步骤仍在Markdown中 |
| 发布白名单扫描 | 通过；没有加入原PDF、MP3、模型、缓存、账户或用户原始材料 |

浏览器预览用本机已安装marked渲染Markdown、用实际Chromium/Edge检查；它近似GitHub排版，**不等于GitHub官方渲染器的逐像素复现**。SVG限制及图片路径另做静态校验，线上文件与自动检查在更新后核对。

## 截图来源

| 文件 | SHA256 |
|---|---|
| learning-preview.png | ef742e3bb06859dfe804f26da5986761f72d6b4a74fffd555e51b789c66d756a |
| audiobook-preview.png | 3a9e2c99223c1a3d55cfb9eec72b4c390295bd32044ba42ac39ca2965f97731d |

两张图均为space-weather-demo示例，2章/2名词。没有把示意界面、历史399词项目或用户私人材料当作本次截图。
