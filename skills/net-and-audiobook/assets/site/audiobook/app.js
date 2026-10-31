(() => {
  "use strict";
  const c = window.AUDIOBOOK_CATALOG, $ = id => document.getElementById(id), audio = $("audio");
  if (!c) { $("title").textContent = "目录未能载入"; return; }
  const key = `nba.${c.project_id}.audio.v1`; let state;
  try { state = JSON.parse(localStorage.getItem(key) || "{}"); } catch (_) { state = {}; }
  if (!state || typeof state !== "object" || Array.isArray(state)) state = {};
  if (state.version !== c.audio_version) state = { version: c.audio_version, speed: 1, positions: {} };
  const speeds = [0.8, 0.9, 1, 1.1, 1.25]; if (!speeds.includes(state.speed)) state.speed = 1;
  if (!state.positions || typeof state.positions !== "object") state.positions = {};
  const save = () => { try { localStorage.setItem(key, JSON.stringify(state)); } catch (_) { $("audio-status").textContent = "无法持久保存播放位置；本次仍可播放。"; } };
  function rate() { audio.defaultPlaybackRate = state.speed; audio.playbackRate = state.speed; $("speed").value = String(state.speed); }
  $("speed").onchange = () => { state.speed = Number($("speed").value); rate(); save(); };
  $("autonext").checked = !!state.autonext; $("autonext").onchange = () => { state.autonext = $("autonext").checked; save(); };
  $("theme").onclick = () => { state.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = state.theme; save(); }; if (state.theme === "dark") document.documentElement.dataset.theme = "dark";
  $("title").textContent = c.title_zh + " · 名词有声书"; document.title = $("title").textContent; $("disclosure").textContent = c.disclosure;
  let current = null, pendingSeek = 0;
  const node = (tag, text) => { const n = document.createElement(tag); if (text != null) n.textContent = text; return n; };
  const duration = n => { n = Math.round(n || 0); return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`; };
  function select(ep, play) {
    if (!ep.ready) return; if (current) { state.positions[current.id] = audio.currentTime; save(); }
    current = ep; state.last = ep.id; pendingSeek = Math.max(0, Number(state.positions[ep.id]) || 0);
    audio.src = ep.audio.split("/").map(encodeURIComponent).join("/") + "?sha=" + ep.sha256; rate(); audio.load();
    $("now").textContent = ep.title_zh; document.querySelectorAll(".episode").forEach(n => n.classList.toggle("active", n.dataset.episode === ep.id));
    $("audio-status").textContent = play ? "正在载入…" : "已恢复上次播放的集数，可继续播放。"; save();
    if (play) audio.play().catch(e => { $("audio-status").textContent = "请点击播放器继续播放：" + e.message; });
  }
  audio.onloadedmetadata = () => { rate(); if (Number.isFinite(audio.duration)) audio.currentTime = Math.min(pendingSeek, Math.max(0, audio.duration - 1)); pendingSeek = 0; $("audio-status").textContent = `实际播放速度 ${audio.playbackRate}× · 英文慢读已包含在音频中`; };
  audio.onplay = rate; audio.onerror = () => { $("audio-status").textContent = "音频未能载入，请检查文件是否完整，或下载 MP3 播放。"; };
  audio.ontimeupdate = () => { if (current && audio.readyState > 0) { state.positions[current.id] = audio.currentTime; save(); } };
  audio.onended = () => { if (!current) return; state.positions[current.id] = 0; save(); if (state.autonext) { const next = c.episodes[c.episodes.indexOf(current) + 1]; if (next?.ready) select(next, true); } };
  $("back").onclick = () => { if (audio.readyState) audio.currentTime = Math.max(0, audio.currentTime - 10); };
  $("forward").onclick = () => { if (Number.isFinite(audio.duration)) audio.currentTime = Math.min(audio.duration, audio.currentTime + 10); };
  function render() {
    const q = $("search").value.trim().toLocaleLowerCase(); $("episodes").replaceChildren(); let shown = 0;
    c.episodes.forEach((ep, i) => { if (!(ep.title_zh + " " + (ep.title_en || "") + " " + ep.terms.map(t => t.zh + " " + t.en).join(" ")).toLocaleLowerCase().includes(q)) return;
      shown++; const box = node("article"); box.className = "card episode"; box.dataset.episode = ep.id; if (current?.id === ep.id) box.classList.add("active");
      box.append(node("p", `EP ${String(i + 1).padStart(2, "0")} · ${ep.term_count} 个术语 · ${ep.ready ? duration(ep.duration_seconds) : "尚未合成"}`), node("h2", ep.title_zh));
      if (ep.title_en) { const en = node("p", ep.title_en); en.className = "english"; box.append(en); }
      const actions = node("div"); actions.className = "episode-actions"; const b = node("button", "播放 / 继续"); b.disabled = !ep.ready; b.onclick = () => select(ep, true); actions.append(b);
      if (ep.ready) { const a = node("a", "下载 MP3"); a.href = ep.audio; a.download = ep.id + ".mp3"; actions.append(a); }
      const t = node("a", "朗读稿"); t.href = `scripts/${ep.id}.txt`; actions.append(t); box.append(actions);
      const details = node("details"); details.append(node("summary", "本集术语"), node("p", ep.terms.map(t => `${t.zh} · ${t.en}`).join("；"))); box.append(details); $("episodes").append(box);
    });
    $("summary").textContent = `${shown} / ${c.episodes.length} 集 · ${c.episodes.reduce((n, ep) => n + ep.term_count, 0)} 个术语`;
    $("bundle").hidden = !c.bundle_ready;
  }
  $("search").oninput = render; render(); rate();
  const last = c.episodes.find(ep => ep.id === state.last && ep.ready); if (last) select(last, false); save();
})();
