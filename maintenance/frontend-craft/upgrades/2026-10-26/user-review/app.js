"use strict";

// These labels are presentation aliases for existing, unmodified artifacts.
// Keep them in agreement with mapping.json; no data fetch is needed for file://.
const scenes = {
  "reading-evidence": {
    name: "阅读与证据核对",
    labels: { jia: "A", yi: "B" },
    states: {
      desktop: [
        { file: "desktop-initial", name: "初始阅读", description: "同一篇资料的初始阅读状态。" },
        { file: "desktop-citation-s2-p2", name: "引用定位 · 原文 2.2", description: "从回答定位到同一篇资料的原文 2.2；观察原文、回答和返回入口。" }
      ],
      mobile: [
        { file: "mobile-initial", name: "初始阅读", description: "同一篇资料的手机初始状态。" },
        { file: "mobile-citation-s2-p2", name: "引用定位 · 原文 2.2", description: "手机视口中定位到原文 2.2 的状态。" }
      ]
    }
  },
  "dense-operations": {
    name: "密集作业管理",
    labels: { jia: "B", yi: "A" },
    states: {
      desktop: [
        { file: "desktop-initial", name: "初始作业列表", description: "同一组十二项作业的初始列表。" },
        { file: "desktop-mixed-retry", name: "混合选择后重试", description: "同一组失败、取消和进行中作业混选重试后的结果。" }
      ],
      mobile: [
        { file: "mobile-initial", name: "初始作业列表", description: "同一组作业的手机初始列表。" }
      ]
    }
  },
  "public-exhibition": {
    name: "作品展示",
    labels: { jia: "A", yi: "B" },
    states: {
      desktop: [
        { file: "desktop-initial", name: "展览首屏", description: "同一展览的页面顶部；两侧均从页首开始。" },
        { file: "desktop-gallery", name: "作品浏览", description: "进入作品区域后的完整视口；布局不同，页面滚动距离不必相同。" },
        { file: "desktop-artwork-02", name: "第二件作品大图", description: "打开同一件作品后的查看状态。" }
      ],
      mobile: [
        { file: "mobile-initial", name: "展览首屏", description: "同一展览在手机视口中的页面顶部。" }
      ]
    }
  }
};

const sceneSelect = document.getElementById("scene");
const viewportSelect = document.getElementById("viewport");
const stateSelect = document.getElementById("state");
const comparison = document.querySelector(".comparison");
const fitButton = document.getElementById("fit");
const pixelsButton = document.getElementById("pixels");
let renderId = 0;

function rebuildStates() {
  const choices = scenes[sceneSelect.value].states[viewportSelect.value];
  stateSelect.replaceChildren(...choices.map((state) => {
    const option = document.createElement("option");
    option.value = state.file;
    option.textContent = state.name;
    return option;
  }));
  render();
}

function render() {
  const currentRender = ++renderId;
  const sceneId = sceneSelect.value;
  const scene = scenes[sceneId];
  const viewport = viewportSelect.value;
  const state = scene.states[viewport].find((entry) => entry.file === stateSelect.value);
  const viewportText = viewport === "desktop" ? "1440 × 1000" : "390 × 844";
  document.getElementById("state-description").textContent = state.description;

  for (const side of ["jia", "yi"]) {
    const alias = side === "jia" ? "方案甲" : "方案乙";
    const label = scene.labels[side];
    const source = `../evidence/canonical/${sceneId}/${label}/${state.file}.jpg`;
    const image = document.getElementById(`image-${side}`);
    const meta = document.getElementById(`meta-${side}`);
    const error = document.getElementById(`error-${side}`);
    image.parentElement.scrollTop = 0;
    image.parentElement.scrollLeft = 0;
    error.hidden = true;
    image.hidden = false;
    image.alt = `${alias}：${scene.name}，${state.name}，${viewport === "desktop" ? "宽屏" : "手机"}原始截图`;
    meta.textContent = `采集视口 ${viewportText} CSS px · 正在载入原图`;
    image.onload = () => {
      if (currentRender !== renderId) return;
      meta.textContent = `采集视口 ${viewportText} CSS px · 图像 ${image.naturalWidth} × ${image.naturalHeight} px`;
    };
    image.onerror = () => {
      if (currentRender !== renderId) return;
      image.hidden = true;
      error.hidden = false;
      meta.textContent = `采集视口 ${viewportText} CSS px · 图片未载入`;
    };
    image.src = source;
    document.getElementById(`original-${side}`).href = source;
    document.getElementById(`app-${side}`).href = `../evidence/runs/${sceneId}/${label}/index.html`;
  }
}

function setSizing(usePixels) {
  comparison.classList.toggle("pixel-size", usePixels);
  fitButton.setAttribute("aria-pressed", String(!usePixels));
  pixelsButton.setAttribute("aria-pressed", String(usePixels));
  document.getElementById("size-note").textContent = usePixels
    ? "原始像素模式：浏览器缩放为 100% 时，1 图像像素对应 1 CSS px；图片区域可以横向和纵向滚动。"
    : "预览会随可用空间缩小，手机图保持其自然宽度；原始图像未经编辑。";
}

sceneSelect.addEventListener("change", rebuildStates);
viewportSelect.addEventListener("change", rebuildStates);
stateSelect.addEventListener("change", render);
fitButton.addEventListener("click", () => setSizing(false));
pixelsButton.addEventListener("click", () => setSizing(true));
rebuildStates();
