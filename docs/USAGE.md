# 使用指南

## 先让代理使用 skill

将`skills/net-and-audiobook/`完整目录载入兼容环境，然后提供真实的材料路径、目标目录及特殊要求。代理先理解来源，再编写带来源记录的project.json；模板不会自动证明论文解释正确。

新站使用独立stage。更新已有网站时先记录原有逐句阅读、云同步、进度和播放器功能，在副本中定点修改，不能直接用新模板覆盖。

## Bash

需要Python 3.10+，ffmpeg/ffprobe在PATH。命令在仓库根运行。

```bash
python -m pip install -r skills/net-and-audiobook/scripts/requirements.txt
python -m pip install playwright
python -m playwright install chromium
SKILL_DIR="$PWD/skills/net-and-audiobook"
WORK="/tmp/net-audiobook-demo"  # 使用新空目录；已有stage不会被覆盖
python "$SKILL_DIR/scripts/make_demo.py" --out "$WORK/input"
python "$SKILL_DIR/scripts/build_site.py" --project "$WORK/input/project.json" \
  --sources-root "$WORK/input" --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" sample --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" build --stage "$WORK/stage"
python "$SKILL_DIR/scripts/verify.py" --stage "$WORK/stage" --audio --package
python "$SKILL_DIR/scripts/browser_check.py" --stage "$WORK/stage" --audio
```

## Windows PowerShell

在仓库根目录运行，选择全新工作目录。可将`python`替换为实际已安装的Python解释器路径。

```powershell
python -m pip install -r skills/net-and-audiobook/scripts/requirements.txt
python -m pip install playwright
python -m playwright install chromium
$skillDir = Join-Path (Get-Location) 'skills/net-and-audiobook'
$demoWork = Join-Path $env:TEMP ('net-audiobook-demo-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python "$skillDir/scripts/make_demo.py" --out "$demoWork/input"
python "$skillDir/scripts/build_site.py" --project "$demoWork/input/project.json" --sources-root "$demoWork/input" --stage "$demoWork/stage"
python "$skillDir/scripts/synthesize.py" sample --stage "$demoWork/stage"
python "$skillDir/scripts/synthesize.py" build --stage "$demoWork/stage"
python "$skillDir/scripts/verify.py" --stage "$demoWork/stage" --audio --package
python "$skillDir/scripts/browser_check.py" --stage "$demoWork/stage" --audio
```

Windows未安装Playwright Chromium时，检查器会尝试本机Edge，也可通过`--browser-executable`指定。需要代理时，在合成命令上显式传`--proxy <已验证代理URL>`，不要照抄别人的本机端口。

## 输出与离线使用

- `stage/index.html`：双语学习网页。
- `stage/audiobook/index.html`：分集播放器。
- `stage/audiobook/audio/`：可直接拷贝到手机的MP3。
- `stage/audiobook/scripts/`：朗读计划与TXT稿件。
- `stage/audiobook/downloads/`：完整ZIP、M3U8列表和手机说明。
- `_work/`：运行状态/缓存，不发布。

语音合成需要联网，完整成品可离线使用。保存完整网站目录，或完整解压MP3包；不要把PWA安装成功当作媒体已全部下载。播放器默认1×，语音内的英文和拼写已经放慢。手机后台播放及自动播放仍受浏览器/应用限制。

## 暂停、恢复与自测

```bash
python "$SKILL_DIR/scripts/synthesize.py" pause --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" status --stage "$WORK/stage"
python "$SKILL_DIR/scripts/synthesize.py" resume --stage "$WORK/stage"
python "$SKILL_DIR/scripts/self_test.py"
```

pause是请求，需确认status中的paused标记/状态。当前有限请求可先进入缓存。续做只跳过计划指纹与成品哈希都一致的集数。不要通过关闭连接窗口、杀全部Python或修改整目录ACL来暂停。

## 验证和发布

验证原文解释与公式，再检查语音和真实浏览器。自动解码、边界与ASR不等于人工听感验收。源码参考：[语音规范](../skills/net-and-audiobook/references/speech.md)、[公式核对](../skills/net-and-audiobook/references/formulas.md)。

```bash
python "$SKILL_DIR/scripts/publish.py" prepare --stage "$WORK/stage" \
  --target "$TARGET" --source-root "$IMMUTABLE_SOURCE_ROOT" --journal "$RELEASE_JOURNAL"
python "$SKILL_DIR/scripts/publish.py" apply --journal "$RELEASE_JOURNAL"
```

先解析这些变量为实际路径。prepare验证当前QA，备份将被覆盖的文件，并记录发布意图；apply检查目标是否发生并发变化。新旧哈希明确的部分发布可以续做，异常文件需先保留并核对。详见[发布与恢复](../skills/net-and-audiobook/references/publishing.md)。

仅在用户明确要求网页先上线时使用`--web-only`并说明音频状态。公开仓库导出需排除用户原件、录音、模型、缓存、凭据和私有日志。仓库自己的原创README截图由单独的文档图片开关和校验处理，不开放任意二进制文件上传。
