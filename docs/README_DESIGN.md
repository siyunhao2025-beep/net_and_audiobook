# README 视觉与来源记录

## 设计目标

- 读者：需要把论文/课程转成学习材料的研究生、教师和科研学习者。
- 一句话价值：从可核对来源的章节计划，生成双语网页与名词有声书。
- 首次成功：提供材料目录，或运行原创小示例；安装步骤和参数保持可复制。
- 视觉：论文页、声波、原文到阅读/聆听的两条航线。真实截图作为证据，SVG只表达身份、机制与顺序。
- 语气：轻松但保留科学限定；“W”彩蛋提醒查定义，不嘲讽作者或编造论文结果。

## 使用并安装的外部 skills

| Skill | 固定版本 | 来源/许可 |
|---|---|---|
| beautify-github-readme | d6562a5f5c484d069f8560b39c215c9cda4b5a55 | [oil-oil/beautify-github-readme](https://github.com/oil-oil/beautify-github-readme/tree/d6562a5f5c484d069f8560b39c215c9cda4b5a55)，MIT |
| crafting-effective-readmes | 3027f20f3181758385a1bb8c022d4041dfb4de84 | [softaworks/agent-toolkit](https://github.com/softaworks/agent-toolkit/tree/3027f20f3181758385a1bb8c022d4041dfb4de84/skills/crafting-effective-readmes)，MIT |
| joke-engineering | e02ec7e226a6e4f8419fd3b88a1d8e472d421b32 | [jwynia/agent-skills](https://github.com/jwynia/agent-skills/tree/e02ec7e226a6e4f8419fd3b88a1d8e472d421b32/skills/creative/humor/joke-engineering)，上游SKILL frontmatter声明MIT |

安装副本保留上游正文、所需资源、版本和许可信息；仅做运行环境frontmatter/UI适配。没有运行来源仓库的安装器、自动钩子或外部二进制下载。第三方skills没有复制进本仓库；这里只记录用途和来源，不把它们变成本项目运行依赖。

## 图形规范

| 元素 | 取值 |
|---|---|
| 深色底/墨色 | #111f2c |
| 暖纸色 | #fff9ec |
| 薄荷强调 | #8cdec3 |
| 珊瑚强调 | #ffa17e |
| 次级文字 | #adc1cb；浅底用#526c70 |
| 字体 | 系统字体及本机中文回退，无远程字体/捆绑字体 |
| SVG | 1200单位宽，完整背景、title/desc、语义alt；无脚本/foreignObject/外链资源 |

封面把原文页与聆听输出放在一起；流程图强调代理理解和脚本执行的不同角色；朗读图只表示经验证的五段顺序。GitHub不播放SVG内动画，因此本次交付静态图，不添加失效动画或大体积循环。

## 可复现资产

```bash
python tools/build_readme_assets.py
python tools/capture_readme_demo.py --stage <已生成音频的原创demo-stage> --out assets/readme
python tools/check_readme.py
```

两张PNG是1440×960真实浏览器截图：原创space-weather-demo，2章/2术语，成品语音已生成。截图不包含浏览器地址栏、用户文献、个人进度或账户。未用示意绘图冒充实际界面。图片仅作为文档资源，原始PDF和MP3不上传。

预览检查900px与390px宽度、明暗背景、资源/链接、SVG文字边界、代码块和折叠段落。关键信息也放在Markdown中，手机缩图或图片不可用时仍能读到使用步骤与机制。

## 本次改动范围

更新README，增加图示、真实演示截图、使用指南和可复现文档工具。公开导出检查器增加显式的README PNG白名单开关，并验证尺寸/格式/元数据；默认继续拒绝未审查的二进制。音频生成、内容顺序、播放速度、站点模板和发布/恢复逻辑不改动。
