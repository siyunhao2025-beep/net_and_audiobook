# project.json 与文件契约

完整原创例子在 `assets/demo-project.json`。用 `make_demo.py --out <新目录>` 生成可实跑的PDF和哈希；例子中的全零SHA只是占位符。

| 顶层字段 | 约束 |
|---|---|
| schema_version | 整数1 |
| project_id | 稳定小写ID，跨版本保留学习进度，不同项目不能共用 |
| title_zh/title_en/summary_zh/summary_en/notes | 标题、概述和来源局限/校订说明 |
| sources | id,title,path,sha256,pages；路径相对输入根，页数来自原件 |
| chapters | 有序id、中英标题、目标、units、2–3道questions、extensions |
| formulas/visuals/terms/episodes | 数量由内容决定，不硬编码历史数量 |
| ui | sequential、timer.focus_minutes/break_minutes，默认40/10 |
| speech | 可选voices:{zh,en}、rates:{term_zh,term_en,spelling,standard_zh,plain_zh} |

内容ID使用 `[a-z0-9][a-z0-9_-]{0,79}`，全局唯一；来源ID另行唯一。来源和图片路径不允许绝对路径、反斜杠、`..`、URL/查询或符号链接。新资源使用PNG/JPEG/WebP，公式用受限MathML或栅格图片。中文/空格文件名通过URL编码处理。

## 章节单元

unit必须含 `id,title_zh,plain_zh,plain_en,standard_zh,standard_en,source_refs`，保证切换英文后仍有完整讲解。可加 `title_en,english,english_role,caveat_zh,formula_ids,visual_ids`。english_role只能是source/translation/explanation。plain_en/standard_en是教学解释，不伪装原句。长文拆成语义单元，不把整章塞成一个打卡点。

source_refs形如 `[{"source_id":"paper-a","page":3}]`，页码从1起且必须存在。可加slide、panel、bbox、note等定位字段，它们不会被读入音频。每道题含zh/en/answer_zh/answer_en/source_refs；延伸方向含zh/en，不能写成已证实结论。

模板呈现“通俗解释→标准解释→英文阅读→公式图表→来源”。要求严格逐句对照时拆小单元，或在原站pairs结构上扩展。不要伪造英语原文。

## 图表与公式

visual含 `id,path,caption_zh,caption_en,read_zh,watch_zh,source_refs`；可另存类型、裁图框与原图号。说明“看什么”与“不能据此断言什么”。算法截图也按visual处理，可读步骤另建来源核对过的单元。

formula含 `id,latex,source_image,verified:true,source_refs`，并有mathml或display_image。verified表示执行者已逐符号比对，程序不能替代这个判断，不能只为过检查填写。source_image必须是真实原文裁图。note_zh记录符号与校订。拒绝控制字符、脚本、外部命名空间/事件属性；精确字体与SVG见formulas.md。

## 名词与分集

term含 `id,zh,en,standard_zh,plain_zh,source_refs`。中文解释不夹英文变量。包含数字/希腊字母/不规则符号的en必须另填明确的字母串spell_as，避免正则漏掉数字；spell_as仅控制拼写，整词仍由en合成。

episode含 `id,title_zh,title_en,chapter_ids,term_ids`。允许一章多集、多小章一集，集内术语不重复，必须覆盖所有名词。刻意跨集复习需注明，统计时区分唯一术语与朗读次数。按主题和实际时长调整，不切断一个名词。

构建器生成 `audiobook/scripts/*.plan.json`与朗读TXT。source_refs只留在计划/网页，TXT不含来源、页码、变量或标签。生成计划与project严格比较；变更文字/声线/顺序时新建stage，不手改计划套旧QA。

## 交付结构

完整网页为index.html、project.js/json、app.js、styles.css、sw.js、app.webmanifest与sources/。audiobook/含独立播放器、catalog、音频、稿件、metrics和下载包。_work/是私有缓存/状态，永不发布。QA绑定当前交付文件哈希，任何改动都会使旧发布证据失效。
