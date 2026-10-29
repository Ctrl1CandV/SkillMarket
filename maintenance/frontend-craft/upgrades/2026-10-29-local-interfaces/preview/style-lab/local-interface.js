/* Fictional local demonstration: no storage, network request, approval or real dispatch. */
(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const form = byId("loan-form");
  const fields = ["venue", "start", "end", "transport", "carrier", "receiver", "confirmed", "note"];
  const read = () => Object.fromEntries(fields.map((id) => [id, id === "confirmed" ? byId(id).checked : byId(id).value]));
  let saved = read();
  let previous = null;
  let revision = 0;
  function message(text, state = "") {
    byId("loan-feedback").textContent = text;
    byId("loan-feedback").dataset.state = state;
  }
  function sync() {
    const pickup = byId("transport").value === "pickup";
    byId("carrier-field").hidden = pickup;
    byId("pickup-field").hidden = !pickup;
    byId("carrier").disabled = pickup;
    byId("carrier").required = !pickup;
    byId("receiver").disabled = !pickup;
    byId("receiver").required = pickup;
    byId("transport-hint").textContent = pickup ? "接收人负责现场核对；自提仍使用专用缓冲箱与照片清单。" : "承运方负责送达与返程，双方按照片清单交接。";
    byId("end").min = byId("start").value || "2027-03-15";
    byId("end").setCustomValidity(byId("end").value && byId("start").value && byId("end").value < byId("start").value ? "归还日期不能早于借出日期。" : "");
    ["venue", "carrier", "receiver"].forEach((id) => byId(id).setCustomValidity(byId(id).required && !byId(id).disabled && !byId(id).value.trim() ? "请填写此项，不能只输入空格。" : ""));
    const dirty = JSON.stringify(read()) !== JSON.stringify(saved);
    byId("loan-dirty").textContent = dirty ? "有未保存修改" : "当前无未保存修改";
    byId("restore").disabled = !dirty;
    byId("undo").hidden = !previous;
    byId("undo").disabled = dirty;
    byId("undo").title = dirty ? "请先保存或恢复当前修改，再撤销上次保存" : "恢复到上次保存前的安排";
    byId("loan-status").textContent = saved.confirmed ? "条件已确认 · 待审批" : "待场馆确认";
    byId("loan-status").className = `status-pill ${saved.confirmed ? "status-organized" : "status-review"}`;
    byId("confirmation-hint").textContent = byId("confirmed").checked ? "保存后更新为“条件已确认 · 待审批”；这不代表获准发运。" : "尚未确认不影响保存；保存后仍显示“待场馆确认”。";
  }
  function write(data) {
    fields.forEach((id) => { if (id === "confirmed") byId(id).checked = data[id]; else byId(id).value = data[id]; });
    sync();
  }
  function record(title, text) {
    const item = document.createElement("li");
    const heading = document.createElement("strong");
    const copy = document.createElement("p");
    heading.textContent = title;
    copy.textContent = text;
    item.append(heading, copy);
    byId("history-list").prepend(item);
    byId("history-count").textContent = `${byId("history-list").children.length} 条`;
  }
  form.addEventListener("input", () => { sync(); message("修改尚未保存；上方状态反映最近一次保存的安排。"); });
  form.addEventListener("change", sync);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sync();
    if (!form.checkValidity()) {
      const invalid = form.querySelector(":invalid");
      message(`尚未保存：请检查${invalid.labels?.[0]?.textContent || "标记的字段"}。`, "error");
      invalid.reportValidity();
      return;
    }
    if (JSON.stringify(read()) === JSON.stringify(saved)) { message("安排没有变化，无需重复保存。"); return; }
    const draft = read();
    const labels = { venue: "接收场馆", start: "借出日期", end: "归还日期", transport: "运输方式", carrier: "承运方", receiver: "接收人", confirmed: "场馆条件", note: "交接备注" };
    const changed = fields.filter((id) => draft[id] !== saved[id]).map((id) => labels[id]);
    previous = { ...saved };
    saved = draft;
    revision += 1;
    record(`本页保存 ${revision}`, `更新了${changed.join("、")}。借展时段：${saved.start} 至 ${saved.end}。`);
    sync();
    message("已保存在当前页面。可查看变更记录，或撤销上次保存；刷新会恢复初始演示。", "saved");
  });
  byId("restore").addEventListener("click", () => { write(saved); message("已恢复最近保存的安排，放弃了本次未保存修改。"); });
  byId("undo").addEventListener("click", () => {
    if (!previous) return;
    saved = previous;
    previous = null;
    write(saved);
    record("撤销最近一次保存", "已恢复保存前的安排；此前记录保留用于查看操作过程。");
    message("已撤销上次保存，安排和状态均已恢复。", "saved");
    form.querySelector('[type="submit"]').focus();
  });
  document.querySelector('a[href="#loan-history"]').addEventListener("click", () => { byId("loan-history").open = true; });
  byId("loan-theme").addEventListener("change", (event) => { document.documentElement.dataset.theme = event.target.value; });
  sync();
})();
