/* Offline-first learning renderer. All prose uses textContent; only build-validated MathML uses HTML. */
(() => {
  "use strict";
  const p = window.LEARNING_PROJECT, $ = id => document.getElementById(id);
  if (!p) { $("overview").textContent = "项目数据未能载入。"; return; }
  const key = `nba.${p.project_id}.study.v1`, unitMap = new Map(), chapterMap = new Map(), mem = {};
  const read = (k, fallback) => { try { return JSON.parse(localStorage.getItem(k)) ?? fallback; } catch (_) { return mem[k] ?? fallback; } };
  const save = () => { try { localStorage.setItem(key, JSON.stringify(state)); } catch (_) { mem[key] = state; $("storage-status").textContent = "浏览器未允许持久保存，请导出进度。"; } };
  const element = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  let state = read(key, {});
  if (!state || typeof state !== "object" || Array.isArray(state)) state = {};
  state.done = Array.isArray(state.done) ? state.done : [];
  p.chapters.forEach(c => { chapterMap.set(c.id, c); c.units.forEach(u => unitMap.set(u.id, { unit: u, chapter: c })); });
  state.done = [...new Set(state.done)].filter(id => unitMap.has(id));
  const initialPosition = state.position; // Capture before observers can update the stored position.
  let active = "overview", restoring = true, observer;
  document.title = p.title_zh; $("site-title").textContent = p.title_zh;
  const preferences = () => {
    document.documentElement.dataset.theme = ["light", "dark"].includes(state.theme) ? state.theme : "light";
    document.documentElement.dataset.lang = ["zh", "en", "both"].includes(state.lang) ? state.lang : "both";
    $("language").textContent = { zh: "中文", en: "English", both: "中英" }[document.documentElement.dataset.lang];
  }; preferences();
  $("theme").onclick = () => { state.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark"; preferences(); save(); };
  $("language").onclick = () => { const a = ["both", "zh", "en"]; state.lang = a[(a.indexOf(document.documentElement.dataset.lang) + 1) % 3]; preferences(); save(); };
  const sourcePath = path => "sources/" + path.split("/").map(encodeURIComponent).join("/");
  function sources(item, parent) {
    const row = element("div", null, "source-links");
    item.source_refs.forEach(r => { const s = p.sources.find(s => s.id === r.source_id); const a = element("a", `${s.title || s.id} · p.${r.page}`); a.href = sourcePath(s.path) + (s.path.toLowerCase().endsWith(".pdf") ? `#page=${r.page}` : ""); a.target = "_blank"; a.rel = "noopener"; row.append(a); });
    parent.append(row);
  }
  function bilingual(parent, zh, en, tag = "p", cls = "") {
    if (zh) parent.append(element(tag, zh, `zh ${cls}`)); if (en) parent.append(element(tag, en, `en english ${cls}`));
  }
  function locked(c) { const i = p.chapters.indexOf(c); return !!p.ui?.sequential && p.chapters.slice(0, i).some(ch => ch.units.some(u => !state.done.includes(u.id))); }
  function show(id, target, replace = false) {
    if (id !== "overview" && (!chapterMap.has(id) || locked(chapterMap.get(id)))) { $("storage-status").textContent = "请先完成前面的章节。"; return; }
    active = id; $("overview").hidden = id !== "overview";
    document.querySelectorAll(".chapter").forEach(n => n.hidden = n.id !== id);
    document.querySelectorAll("[data-chapter]").forEach(n => n.setAttribute("aria-current", String(n.dataset.chapter === id)));
    document.body.classList.remove("menu-open"); $("menu").setAttribute("aria-expanded", "false");
    state.chapter = id; if (!restoring) { state.position = target || id; save(); }
    history[replace ? "replaceState" : "pushState"]({}, "", "#" + (target || id));
    requestAnimationFrame(() => { if (target) $(target)?.scrollIntoView(); else window.scrollTo(0, 0); });
  }
  function paint() {
    state.done = state.done.filter(id => unitMap.has(id));
    $("progress").textContent = `${state.done.length} / ${unitMap.size} 个知识点 · ${state.done.length * 10} XP`;
    $("progress-bar").value = unitMap.size ? state.done.length / unitMap.size * 100 : 0;
    document.querySelectorAll("[data-unit-check]").forEach(b => { const yes = state.done.includes(b.dataset.unitCheck); b.setAttribute("aria-pressed", String(yes)); b.textContent = yes ? "已完成 · 撤销" : "完成此节"; b.closest(".unit").classList.toggle("done", yes); });
    document.querySelectorAll("[data-all]").forEach(b => { const c = chapterMap.get(b.dataset.all); b.textContent = c.units.every(u => state.done.includes(u.id)) ? "撤销本章打卡" : "完成整章"; });
    document.querySelectorAll("[data-chapter]").forEach(b => { const c = chapterMap.get(b.dataset.chapter); if (c) b.textContent = `${locked(c) ? "🔒 " : ""}${c.title_zh} · ${c.units.filter(u => state.done.includes(u.id)).length}/${c.units.length}`; });
    // Undoing an earlier chapter must also close a now-locked later chapter.
    if (active !== "overview" && locked(chapterMap.get(active))) show("overview");
  }
  const overview = $("overview"); bilingual(overview, p.title_zh, p.title_en, "h2");
  bilingual(overview, p.summary_zh || "按章节学习，逐节打卡。", p.summary_en);
  overview.append(element("p", `${p.chapters.length} 章 · ${unitMap.size} 个知识点 · ${(p.formulas || []).length} 条公式 · ${p.terms.length} 个术语`, "meta"));
  (p.notes || []).forEach(n => overview.append(element("p", n, "notice")));
  const glossary = element("details"); glossary.append(element("summary", "名词索引 / Glossary"));
  p.terms.forEach(t => { const d = element("div", null, "card"); bilingual(d, t.zh, t.en, "h3"); d.append(element("p", t.plain_zh, "zh plain"), element("p", t.standard_zh, "zh")); sources(t, d); glossary.append(d); }); overview.append(glossary);
  const formulaMap = new Map((p.formulas || []).map(x => [x.id, x])), visualMap = new Map((p.visuals || []).map(x => [x.id, x]));
  p.chapters.forEach(c => {
    const button = element("button"); button.dataset.chapter = c.id; button.onclick = () => show(c.id); $("chapters").append(button);
    const section = element("section", null, "chapter"); section.id = c.id; section.hidden = true;
    bilingual(section, c.title_zh, c.title_en, "h2"); if (c.goal_zh) section.append(element("p", c.goal_zh, "zh"));
    const all = element("button", "完成整章"); all.dataset.all = c.id; all.onclick = () => { const complete = c.units.every(u => state.done.includes(u.id)); const ids = new Set(state.done); c.units.forEach(u => complete ? ids.delete(u.id) : ids.add(u.id)); state.done = [...ids]; save(); paint(); }; section.append(all);
    c.units.forEach(u => {
      const box = element("article", null, "unit"); box.id = u.id; box.dataset.unit = u.id;
      const head = element("div", null, "unit-head"), title = element("div"), check = element("button", "完成此节"); bilingual(title, u.title_zh, u.title_en, "h3"); check.dataset.unitCheck = u.id; check.onclick = () => { state.done = state.done.includes(u.id) ? state.done.filter(x => x !== u.id) : [...state.done, u.id]; save(); paint(); }; head.append(title, check); box.append(head);
      bilingual(box, "通俗地说，" + u.plain_zh.replace(/^通俗[地的]说[，,：:]?\s*/, ""), u.plain_en, "p", "plain");
      const standard = element("div"); standard.append(element("span", "标准解释 / Standard explanation", "label")); bilingual(standard, u.standard_zh, u.standard_en); box.append(standard);
      if (u.english) { box.append(element("p", ({source: "原文 / Source", translation: "译文 / Translation", explanation: "补充讲解 / Explanation"})[u.english_role], "en meta")); box.append(element("p", u.english, "en english")); }
      if (u.caveat_zh) box.append(element("p", u.caveat_zh, "zh notice"));
      (u.formula_ids || []).forEach(id => { const f = formulaMap.get(id), d = element("div", null, "formula"); d.dataset.formula = id;
        if (f.mathml) d.innerHTML = f.mathml; else { const img = element("img"); img.src = sourcePath(f.display_image); img.alt = f.alt_zh || "经核对的公式"; d.append(img); }
        const details = element("details"); details.append(element("summary", "核对原式 / Compare source")); const im = element("img"); im.src = sourcePath(f.source_image); im.alt = "来源公式截图"; details.append(im); d.append(details);
        if (f.note_zh) d.append(element("p", f.note_zh, "formula-note")); sources(f, d); box.append(d); });
      (u.visual_ids || []).forEach(id => { const v = visualMap.get(id), f = element("figure"), img = element("img"); img.src = sourcePath(v.path); img.alt = v.caption_zh; img.loading = "lazy"; img.tabIndex = 0;
        const open = () => { $("large-image").src = img.src; $("large-image").alt = img.alt; $("large-caption").textContent = v.caption_zh; $("lightbox").showModal(); }; img.onclick = open; img.onkeydown = e => { if (e.key === "Enter") open(); };
        const caption = element("figcaption"); bilingual(caption, v.caption_zh, v.caption_en); caption.append(element("p", v.read_zh, "zh"), element("p", v.watch_zh, "zh notice")); f.append(img, caption); sources(v, f); box.append(f); });
      sources(u, box); section.append(box);
    });
    const quiz = element("section", null, "quiz"); quiz.append(element("h3", "想一想 / Check your understanding"));
    c.questions.forEach(q => { const d = element("details"), s = element("summary"); bilingual(s, q.zh, q.en, "span"); d.append(s); bilingual(d, q.answer_zh, q.answer_en); sources(q, d); quiz.append(d); });
    (c.extensions || []).forEach(x => bilingual(quiz, x.zh, x.en)); section.append(quiz); $("lessons").append(section);
  });
  $("home").onclick = e => { e.preventDefault(); show("overview"); };
  $("menu").onclick = () => { const open = document.body.classList.toggle("menu-open"); $("menu").setAttribute("aria-expanded", String(open)); };
  $("search").oninput = () => { const q = $("search").value.trim().toLocaleLowerCase(); $("results").replaceChildren(); if (!q) return;
    let n = 0; unitMap.forEach(({ unit: u, chapter: c }) => { if (JSON.stringify(u).toLocaleLowerCase().includes(q)) { n++; if (n <= 40) { const b = element("button", `${locked(c) ? "🔒 " : ""}${c.title_zh} · ${u.title_zh}`); b.onclick = () => show(c.id, u.id); $("results").append(b); } } }); $("results").prepend(element("p", `${n} 个结果`, "meta")); };
  $("export").onclick = () => { const a = element("a"); const url = URL.createObjectURL(new Blob([JSON.stringify({ schema_version: 1, project_id: p.project_id, state }, null, 2)], { type: "application/json" })); a.href = url; a.download = `${p.project_id}-progress.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
  $("import").onchange = async e => { try { const f = e.target.files[0]; if (!f || f.size > 2000000) throw Error("文件过大"); const x = JSON.parse(await f.text());
    if (x.project_id !== p.project_id || x.schema_version !== 1 || !Array.isArray(x.state?.done)) throw Error("进度属于其他项目或格式不正确");
    state.done = [...new Set(x.state.done)].filter(id => unitMap.has(id)); if (["zh", "en", "both"].includes(x.state.lang)) state.lang = x.state.lang; if (["light", "dark"].includes(x.state.theme)) state.theme = x.state.theme;
    state.position = unitMap.has(x.state.position) ? x.state.position : null; preferences(); save(); paint(); $("storage-status").textContent = "进度已导入。";
  } catch (err) { $("storage-status").textContent = "导入失败：" + err.message; } finally { e.target.value = ""; } };
  $("lightbox-close").onclick = () => $("lightbox").close(); $("lightbox").onclick = e => { if (e.target === $("lightbox")) $("lightbox").close(); };
  const minutes = p.ui?.timer || {}, limits = { focus: (minutes.focus_minutes || 40) * 60000, break: (minutes.break_minutes || 10) * 60000 };
  state.timer ||= {}; let phase = state.timer.phase === "break" ? "break" : "focus", remaining = Number(state.timer.remaining);
  if (!Number.isFinite(remaining) || remaining <= 0 || remaining > limits[phase]) remaining = limits[phase];
  let running = false, tick = performance.now(), lastSaved = tick;
  function clock() {
    const now = performance.now(), delta = Math.max(0, Math.min(2000, now - tick)); tick = now;
    const engaged = running && !document.hidden && (phase === "break" || active !== "overview");
    if (engaged) remaining -= delta;
    if (remaining <= 0) { phase = phase === "focus" ? "break" : "focus"; remaining = limits[phase]; if (phase === "break") $("break-dialog").showModal(); else running = false; }
    const secs = Math.ceil(remaining / 1000); $("timer").textContent = `${phase === "focus" ? "学习" : "休息"} ${String(Math.floor(secs / 60)).padStart(2, "0")}:${String(secs % 60).padStart(2, "0")}${running && !engaged ? " · 已自动暂停" : ""}`;
    $("timer-toggle").textContent = running ? "暂停计时" : "开始计时";
    state.timer = { phase, remaining }; if (now - lastSaved > 5000) { save(); lastSaved = now; }
  }
  $("timer-toggle").onclick = () => { running = !running; tick = performance.now(); clock(); save(); };
  $("break-close").onclick = () => $("break-dialog").close(); document.addEventListener("visibilitychange", () => { tick = performance.now(); save(); }); window.addEventListener("pagehide", save); setInterval(clock, 250); clock();
  paint();
  const hash = decodeURIComponent(location.hash.slice(1)), target = hash || initialPosition || state.chapter;
  const chapter = unitMap.get(target)?.chapter.id || (chapterMap.has(target) ? target : "overview"); show(locked(chapterMap.get(chapter) || p.chapters[0]) && chapter !== "overview" ? "overview" : chapter, unitMap.has(target) ? target : null, true);
  requestAnimationFrame(() => requestAnimationFrame(() => { restoring = false;
    observer = new IntersectionObserver(entries => { if (restoring || active === "overview") return; const hit = entries.filter(x => x.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]; if (hit) { state.position = hit.target.id; save(); } }, { rootMargin: "-90px 0px -50% 0px" });
    document.querySelectorAll(".unit").forEach(n => observer.observe(n));
  }));
  window.onpopstate = () => { const id = decodeURIComponent(location.hash.slice(1)); show(unitMap.get(id)?.chapter.id || (chapterMap.has(id) ? id : "overview"), unitMap.has(id) ? id : null, true); };
  if ("serviceWorker" in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register("sw.js").catch(() => {});
})();
