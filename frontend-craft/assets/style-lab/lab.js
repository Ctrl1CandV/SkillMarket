/* Entirely local interactions. No network, analytics, storage or simulated API. */
(() => {
  "use strict";

  const root = document.documentElement;
  const announcement = document.getElementById("app-announcement");
  const themes = new Set(["neutral-cobalt", "ink-cyan", "paper-berry"]);
  const viewNames = {
    reader: "阅读与核对",
    library: "资料列表",
    components: "组件与状态"
  };
  const viewButtons = [...document.querySelectorAll("[data-view]")];
  const panels = [...document.querySelectorAll(".view-panel")];
  let highlightTimeout;
  let highlightedTarget = null;

  function announce(message) {
    announcement.textContent = message;
  }

  function setView(view, focusHeading = false) {
    if (!Object.hasOwn(viewNames, view)) return;
    panels.forEach((panel) => {
      panel.hidden = panel.id !== `view-${view}`;
    });
    viewButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.view === view));
    });
    announce(`已切换到${viewNames[view]}。`);
    if (focusHeading) {
      const heading = document.getElementById(`${view}-heading`);
      if (heading) {
        heading.scrollIntoView({ block: "start", behavior: "auto" });
        heading.focus({ preventScroll: true });
      }
    }
  }

  viewButtons.forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view, true));
  });

  document.querySelectorAll('input[name="theme"]').forEach((input) => {
    input.addEventListener("change", () => {
      if (!input.checked || !themes.has(input.value)) return;
      root.dataset.theme = input.value;
      announce(`主题已切换为${input.nextElementSibling.textContent.trim()}，只在本页生效。`);
    });
  });

  function locate(target) {
    if (!target) return;
    const panel = target.closest(".view-panel");
    if (panel) setView(panel.id.replace("view-", ""));
    if (highlightedTarget) highlightedTarget.classList.remove("active-target");
    window.clearTimeout(highlightTimeout);
    target.classList.add("active-target");
    highlightedTarget = target;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView({ block: "start", behavior: reducedMotion ? "auto" : "smooth" });
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
    announce(target.id.startsWith("source-") ? "已定位到对应原文。段末引用可返回核对说明。" : "已定位到相应内容。");
    highlightTimeout = window.setTimeout(() => {
      target.classList.remove("active-target");
      if (highlightedTarget === target) highlightedTarget = null;
    }, 2200);
  }

  document.querySelectorAll("[data-locate]").forEach((link) => {
    link.addEventListener("click", (event) => {
      const id = link.getAttribute("href").slice(1);
      const target = document.getElementById(id);
      if (!target) return;
      event.preventDefault();
      locate(target);
    });
  });

  document.querySelectorAll("[data-open-reader]").forEach((button) => {
    button.addEventListener("click", () => setView("reader", true));
  });

  const noteInput = document.getElementById("note-input");
  const noteError = document.getElementById("note-error");
  const notePreview = document.getElementById("note-preview");
  const notePreviewText = document.getElementById("note-preview-text");
  document.getElementById("preview-note").addEventListener("click", () => {
    const value = noteInput.value.trim();
    if (!value) {
      noteError.hidden = false;
      noteInput.setAttribute("aria-invalid", "true");
      noteInput.setAttribute("aria-describedby", "note-hint note-error");
      noteInput.focus();
      return;
    }
    noteError.hidden = true;
    noteInput.removeAttribute("aria-invalid");
    noteInput.setAttribute("aria-describedby", "note-hint");
    notePreviewText.textContent = value;
    notePreview.hidden = false;
    announce("批注已在当前页面预览，刷新后清除。没有上传或持久保存。");
  });
  noteInput.addEventListener("input", () => {
    if (noteInput.value.trim()) {
      noteError.hidden = true;
      noteInput.removeAttribute("aria-invalid");
      noteInput.setAttribute("aria-describedby", "note-hint");
    }
  });

  const searchInput = document.getElementById("document-search");
  const statusFilter = document.getElementById("status-filter");
  const clearFilters = document.getElementById("clear-filters");
  const documentList = document.getElementById("document-list");
  const rows = [...documentList.querySelectorAll(".document-row")];
  const emptyState = document.getElementById("list-empty");
  const resultCount = document.getElementById("result-count");

  function applyFilters() {
    const query = searchInput.value.trim().toLocaleLowerCase("zh-CN");
    const status = statusFilter.value;
    let count = 0;
    rows.forEach((row) => {
      const content = row.querySelector(".row-content").textContent.toLocaleLowerCase("zh-CN");
      const matches = content.includes(query) && (status === "all" || row.dataset.status === status);
      row.hidden = !matches;
      if (matches) count += 1;
    });
    documentList.hidden = count === 0;
    emptyState.hidden = count !== 0;
    resultCount.textContent = query || status !== "all" ? `筛选结果 ${count} 篇，共 ${rows.length} 篇样稿` : `当前显示 ${count} 篇`;
    clearFilters.disabled = !query && status === "all";
  }

  function resetFilters() {
    searchInput.value = "";
    statusFilter.value = "all";
    applyFilters();
    announce(`筛选已清空，显示全部 ${rows.length} 篇原创样稿。`);
  }

  document.getElementById("filter-form").addEventListener("submit", (event) => {
    event.preventDefault();
    applyFilters();
  });
  searchInput.addEventListener("input", applyFilters);
  statusFilter.addEventListener("change", applyFilters);
  clearFilters.addEventListener("click", resetFilters);
  document.querySelectorAll("[data-reset-filters]").forEach((button) => {
    button.addEventListener("click", () => {
      resetFilters();
      searchInput.focus();
    });
  });

  document.querySelectorAll("[data-disclosure]").forEach((button) => {
    button.addEventListener("click", () => {
      const details = document.getElementById(button.dataset.disclosure);
      if (!details) return;
      const expanded = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(expanded));
      details.hidden = !expanded;
      button.firstChild.textContent = expanded ? "收起摘要 " : "展开摘要 ";
      button.querySelector("span").textContent = expanded ? "−" : "+";
    });
  });

  const sampleForm = document.getElementById("sample-form");
  const titleInput = document.getElementById("sample-title");
  const titleError = document.getElementById("title-error");
  const formFeedback = document.getElementById("form-feedback");
  sampleForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!titleInput.value.trim()) {
      titleInput.setAttribute("aria-invalid", "true");
      titleInput.setAttribute("aria-describedby", "title-hint title-error");
      titleError.hidden = false;
      formFeedback.hidden = true;
      titleInput.focus();
      announce("资料标题为空，请填写标题。");
      return;
    }
    titleInput.removeAttribute("aria-invalid");
    titleInput.setAttribute("aria-describedby", "title-hint");
    titleError.hidden = true;
    formFeedback.textContent = "本页输入检查通过。未提交数据，也未执行保存。";
    formFeedback.hidden = false;
  });
  titleInput.addEventListener("input", () => {
    formFeedback.hidden = true;
    if (titleInput.value.trim()) {
      titleInput.removeAttribute("aria-invalid");
      titleInput.setAttribute("aria-describedby", "title-hint");
      titleError.hidden = true;
    }
  });
  document.getElementById("reset-form").addEventListener("click", () => {
    sampleForm.reset();
    titleInput.removeAttribute("aria-invalid");
    titleInput.setAttribute("aria-describedby", "title-hint");
    titleError.hidden = true;
    formFeedback.hidden = true;
    announce("输入示例已恢复。");
  });

  const stateSelector = document.getElementById("state-selector");
  const stateStage = document.getElementById("state-stage");
  const statePanels = [...document.querySelectorAll("[data-state-content]")];
  const states = new Set(statePanels.map((panel) => panel.dataset.stateContent));
  function setDemoState(state) {
    if (!states.has(state)) return;
    stateSelector.value = state;
    stateStage.dataset.state = state;
    statePanels.forEach((panel) => {
      panel.hidden = panel.dataset.stateContent !== state;
    });
  }
  stateSelector.addEventListener("change", () => setDemoState(stateSelector.value));
  document.querySelectorAll("[data-demo-state]").forEach((button) => {
    button.addEventListener("click", () => {
      setDemoState(button.dataset.demoState);
      stateSelector.focus({ preventScroll: true });
    });
  });

  const selectedCheckbox = document.getElementById("combined-selected");
  const warningCheckbox = document.getElementById("combined-warning");
  const combinedItem = document.getElementById("combined-item");
  const warningMessage = document.getElementById("combined-warning-message");
  function updateCombinedState() {
    combinedItem.dataset.selected = String(selectedCheckbox.checked);
    combinedItem.setAttribute("aria-pressed", String(selectedCheckbox.checked));
    warningMessage.hidden = !warningCheckbox.checked;
    if (warningCheckbox.checked) combinedItem.setAttribute("aria-describedby", "combined-warning-message");
    else combinedItem.removeAttribute("aria-describedby");
  }
  selectedCheckbox.addEventListener("change", updateCombinedState);
  warningCheckbox.addEventListener("change", updateCombinedState);
  combinedItem.addEventListener("click", () => {
    selectedCheckbox.checked = !selectedCheckbox.checked;
    updateCombinedState();
  });

  applyFilters();
  updateCombinedState();
})();
