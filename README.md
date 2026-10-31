# 空间天气网页 + 有声书 Skill

把空间天气、空间物理及相关论文、PDF和课程材料，做成**有来源可查的分章节双语学习网页**与**专业名词有声书**。核心入口：[SKILL.md](skills/net-and-audiobook/SKILL.md)。

本skill提炼自两套已完成的本地项目：14份课程PDF、1篇风场论文、25集有声书与399个名词。逐文件技术审计覆盖588个文件、69个子目录；公开仓库仅包含流程、原创模板、脚本和去标识化统计，不包含用户原文、成品音频、模型或私人配置。

## 直接交给代理的任务示例

```text
使用 $net-and-audiobook，读取我指定的论文/PPT目录，按章节制作双语学习网页和名词有声书。
沿用晓晓普通话和 Jenny 美式英语：中文名词、英文慢读、完整拼写、中文标准解释，
然后“通俗地说，……”；不读公式、复杂变量、PPT来源和页码。
先在独立目录完成检查，再发布到我指定的位置。
```

将 `skills/net-and-audiobook/` 整个目录载入支持SKILL.md的代理环境，不只复制一份提示词。执行代理还需能读取你的实际文件；远程Windows可通过已连接的Desktop Commander访问，需要上传GitHub时使用GitHub插件。

## 已包含

- 全目录清点、SHA、逐页PDF提取、图像解码、音频完整解码和ZIP检查，明确区分技术检查与人工理解/试听。
- 来源ID与页码、分章节中英讲解、通俗/标准解释、自测题、图表与原式核对。
- 不依赖CDN的静态网页、手机布局、主题/语言切换、搜索、逐节打卡、进度导入导出、恢复位置、40/10计时。
- 自然普通话/美式英语原生慢速生成、完整拼写、缓存、暂停续做、MP3、下载包与手机说明。
- 结构/音频检查、HTTP/file与桌面/手机浏览器检查、发布备份、并发修改检测及回滚。
- 风场分量、TIDI/SABER数据角色、重建与预测、GAN物理约束等领域解释规则。

模板默认本机存档。旧项目的云同步、SVG公式与逐句阅读等扩展流程保存在references中，需要按具体项目保留并测试；不捆绑真实云环境或第三方SDK。

## 本地跑一个原创小示例

需要Python 3.10+、ffmpeg/ffprobe。以下为Bash示例；Windows用已安装Python执行同名脚本并传入对应路径。

```bash
python -m pip install -r skills/net-and-audiobook/scripts/requirements.txt
python -m pip install playwright
python -m playwright install chromium

SKILL_DIR="$PWD/skills/net-and-audiobook"
WORK="/tmp/net-audiobook-demo"
python "$SKILL_DIR/scripts/make_demo.py" --out "$WORK/input"
python "$SKILL_DIR/scripts/build_site.py" --project "$WORK/input/project.json" \
  --sources-root "$WORK/input" --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" sample --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" build --stage "$WORK/stage"
python "$SKILL_DIR/scripts/verify.py" --stage "$WORK/stage" --audio --package
python "$SKILL_DIR/scripts/browser_check.py" --stage "$WORK/stage" --audio
```

选择全新空的WORK路径；重复构建会拒绝覆盖原stage。Windows无已安装Chromium时，检查器会尝试本机Edge；也可指定`--browser-executable`。需要代理时显式传`--proxy`，不照抄其他机器的端口。

生成后打开`$WORK/stage/index.html`或`audiobook/index.html`。**在线生成语音，离线播放成品**；完整离线使用需保存整个站点/下载MP3，PWA应用壳缓存不等于所有媒体已下载。对私密材料，先确定允许发送给所选TTS服务，再运行联网生成。

## 音频格式

| 顺序 | 内容 | 原生语速 |
|---|---|---|
| 1 | 中文名词 | -8% |
| 2 | Jenny美式英语整词/短语 | -30%，约0.7× |
| 3 | Jenny完整字母拼写 | -20%，约0.8× |
| 4 | 中文标准解释 | -3% |
| 5 | “通俗地说，…” | -3% |

各段保留停顿，播放器默认1×。不使用裁短字母音库或后期拉伸。48kHz单声道128kbps MP3；自动QA不能替代对重音、完整尾音和自然度的试听。

## 暂停、继续和验证

```bash
python "$SKILL_DIR/scripts/synthesize.py" pause --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" status --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" resume --stage "$WORK/stage"
python "$SKILL_DIR/scripts/self_test.py"
```

pause是请求安全暂停，需读status确认当前任务已停；当前有限请求会先进入缓存。续做仅跳过计划指纹和音频SHA均一致的集数。发布工具先prepare备份与意图，再apply；已有网站先记录功能基线并在副本里定点修改，不能直接拿新模板覆盖。

## 证据与边界

实际测试、修正与限制见[验证记录](quality/VALIDATION.md)，来源覆盖见[审计摘要](quality/source-audit-summary.json)。本地自测不需要联网生成音频；GitHub CI只跑离线契约检查和JS语法，不把测试音频当自然语音样本。

教学内容、翻译、公式等价和未定义符号仍须逐页核对。第三方依赖从维护者处安装，各自许可与语音服务条件独立适用；本仓库不分发字体、SDK、权重或用户教材。
