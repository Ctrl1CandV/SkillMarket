/* Demonstration state stays in this page. Refresh resets it. */
(() => {
  "use strict";
  const palettes = window.CraftPalettes;
  const requested = new URLSearchParams(location.search).get("palette");
  const palette = palettes.find(item => item.id === requested) || palettes[0];
  document.documentElement.dataset.palette = palette.id;
  function syncLinks(id) {
    document.querySelectorAll('a[href]').forEach(link => {
      const href = link.getAttribute('href');
      if (href.startsWith("#")) return;
      const url = new URL(href, location.href);
      if (url.origin !== location.origin || url.pathname.slice(0, url.pathname.lastIndexOf("/")) !== location.pathname.slice(0, location.pathname.lastIndexOf("/"))) return;
      if (!/^(index|workbench|editorial|showcase)\.html$/.test(url.pathname.split("/").pop())) return;
      url.searchParams.set("palette", id);
      link.href = url;
    });
  }
  syncLinks(palette.id);
  const picker = document.getElementById("palette-picker");
  palettes.forEach(item => {
    const option = document.createElement("option");
    option.value = item.id; option.textContent = item.name; option.selected = item.id === palette.id;
    picker.append(option);
  });
  picker.addEventListener("change", () => {
    document.documentElement.dataset.palette = picker.value;
    syncLinks(picker.value);
    const url = new URL(location.href); url.searchParams.set("palette", picker.value);
    try { history.replaceState(null, "", url); } catch (_) { /* file URLs may restrict history; preview still works. */ }
    document.getElementById("palette-announcement").textContent = `已切换为${picker.selectedOptions[0].textContent}。`;
  });
  const records = {
    shoreline: { title:"退潮之后：河口声音与步行路线记录", kind:"声音 / Field recording", duration:"18 分 24 秒", status:"需要补充许可", warning:"录音中的访谈片段尚未确认公开许可。可整理草稿，发布前需完成核对。", defaultName:"河口步行记录 · 第一辑" },
    greenhouse: { title:"温室边缘的日常：旧植物园观察札记", kind:"图文 / Field notes", duration:"12 张图 · 860 字", status:"内容已核对", warning:"图像和文字均为本地演示素材，记录可继续编辑；没有执行真实发布。", defaultName:"旧植物园观察 · 午后" },
    alley: { title:"巷子里的修理铺与一张手绘地图", kind:"图文 / Visual essay", duration:"8 张图 · 1,240 字", status:"等待复核", warning:"手绘地图中的两处地名需要复核。保留原始备注，避免把暂定信息当成结论。", defaultName:"修理铺地图 · 城南" },
    night: { title:"末班车到站以前：夜间公共空间的片刻", kind:"声音 / Sound walk", duration:"09 分 36 秒", status:"内容已核对", warning:"录音资料已完成内部核对。此页仅演示样式与本地草稿编辑，不上传文件。", defaultName:"末班车之前 · 声音片段" }
  };
  document.querySelectorAll("[data-record]").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll("[data-record]").forEach(other => { const selected = other === button; other.setAttribute("aria-pressed", String(selected)); other.querySelector(".record-indicator").textContent = selected ? "●" : "○"; });
    const record = records[button.dataset.record];
    document.getElementById("detail-title").textContent = record.title;
    document.getElementById("record-kind").textContent = record.kind;
    document.getElementById("record-duration").textContent = record.duration;
    document.getElementById("record-status").textContent = record.status;
    document.getElementById("record-warning").textContent = record.warning;
    const checked = record.status === "内容已核对";
    document.getElementById("record-notice").className = `notice ${checked ? "success" : "warning"}`;
    document.getElementById("notice-title").textContent = checked ? "✓ 内容核对完成" : "! 待核对事项";
    document.getElementById("delivery-name").value = record.defaultName;
    document.getElementById("delivery-name").removeAttribute("aria-invalid");
    document.getElementById("name-error").hidden = true;
    document.getElementById("save-status").textContent = "";
    document.getElementById("work-detail").dataset.current = button.dataset.record;
  }));
  const form = document.getElementById("draft-form");
  if (form) {
    const input = document.getElementById("delivery-name");
    form.addEventListener("submit", event => {
      event.preventDefault();
      const invalid = !input.value.trim();
      input.setAttribute("aria-invalid", String(invalid));
      document.getElementById("name-error").hidden = !invalid;
      if (invalid) { input.focus(); document.getElementById("save-status").textContent = ""; return; }
      const id = document.getElementById("work-detail").dataset.current;
      records[id].defaultName = input.value.trim();
      document.getElementById("save-status").textContent = "✓ 草稿已在本页保存，刷新后重置。";
    });
    document.getElementById("reset-draft").addEventListener("click", () => {
      input.value = records[document.getElementById("work-detail").dataset.current].defaultName;
      input.removeAttribute("aria-invalid"); document.getElementById("name-error").hidden = true;
      document.getElementById("save-status").textContent = "已恢复最近一次保存的名称。";
    });
  }
  const bookmark = document.getElementById("bookmark");
  if (bookmark) bookmark.addEventListener("click", () => {
    const selected = bookmark.getAttribute("aria-pressed") !== "true";
    bookmark.setAttribute("aria-pressed", String(selected));
    bookmark.textContent = selected ? "✓ 已加入本页阅读清单" : "加入本页阅读清单";
    document.getElementById("bookmark-status").textContent = selected ? "本页已记住此选择，刷新后重置。" : "已从本页阅读清单移除。";
  });
})();
