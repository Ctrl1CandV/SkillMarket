(() => {
  "use strict";
  const palettes = window.CraftPalettes;
  const grid = document.getElementById("palette-grid");
  const output = document.getElementById("css-output");
  const requested = new URLSearchParams(location.search).get("palette");
  let selected = palettes.find(item => item.id === requested) || palettes[0];
  palettes.forEach((palette, index) => {
    const button = document.createElement("button"); button.type = "button";
    button.className = "palette-card"; button.dataset.palette = palette.id;
    button.setAttribute("aria-pressed", "false"); button.setAttribute("aria-label", `选择${palette.name}`);
    button.innerHTML = `<span class="mini-page" aria-hidden="true"><span class="mini-brand"><span>SHORELINE / 04</span><strong>把城市，<br>重新看见。</strong><i></i></span><span class="mini-surface"><b>现场观察札记</b><span class="mini-line"></span><span class="mini-line short"></span><span class="mini-selection">● 河口步行记录</span><span class="mini-action">继续整理 ↗</span></span></span><span class="card-copy"><span class="card-title">${palette.name}<span class="card-index">${String(index+1).padStart(2,"0")}</span></span><span class="card-description">${palette.label}</span><span class="card-selected">选择此搭配 →</span></span>`;
    button.addEventListener("click", () => select(palette)); grid.append(button);
  });
  function select(palette, announce = true) {
    selected = palette;
    grid.querySelectorAll(".palette-card").forEach(button => {
      const active = button.dataset.palette === palette.id;
      button.setAttribute("aria-pressed", String(active));
      button.querySelector(".card-selected").textContent = active ? "✓ 当前搭配" : "选择此搭配 →";
    });
    document.querySelector(".selected-recipe").dataset.palette = palette.id;
    document.getElementById("selected-name").textContent = palette.name;
    document.getElementById("selected-number").textContent = String(palettes.indexOf(palette)+1).padStart(2,"0");
    document.getElementById("selected-relation").textContent = palette.relation;
    document.getElementById("selected-caution").textContent = palette.caution;
    ["workbench","editorial","showcase"].forEach(view => { document.getElementById(`open-${view}`).href = `${view}.html?palette=${palette.id}`; });
    const styles = getComputedStyle(grid.querySelector(`[data-palette="${palette.id}"]`));
    output.value = `/* Original Frontend Craft recipe: ${palette.name}\n   Recheck pairings after adapting to real content. Font and radius are optional. */\n:root {\n  color-scheme: ${styles.colorScheme};\n${window.CraftColorRoles.map(role => `  --cs-${role}: ${styles.getPropertyValue(`--cs-${role}`).trim()};`).join("\n")}\n}\n`;
    document.getElementById("export-status").textContent = "";
    const url = new URL(location.href); url.searchParams.set("palette", palette.id);
    try { history.replaceState(null, "", url); } catch (_) { /* file URL restrictions do not prevent selecting or exporting. */ }
    if (announce) document.getElementById("selection-announcement").textContent = `已选择${palette.name}。上方三个模板入口与下方导出内容已更新。`;
  }
  select(selected, false);
  document.getElementById("copy-css").addEventListener("click", async () => {
    const text = output.value;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      document.getElementById("export-status").textContent = "已复制当前配色 CSS。";
    } catch (_) {
      document.getElementById("export-details").open = true; output.focus(); output.select();
      document.getElementById("export-status").textContent = "自动复制不可用；CSS 已展开并选中，可手动复制或下载。";
    }
  });
  document.getElementById("download-css").addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob([output.value], {type:"text/css;charset=utf-8"}));
    const link = document.createElement("a"); link.href = url; link.download = `color-${selected.id}.css`;
    document.body.append(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    document.getElementById("export-status").textContent = `已发起 color-${selected.id}.css 下载。`;
  });
})();
