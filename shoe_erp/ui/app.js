/* ============================================================
   奥登科鞋业 · 中文 ERP 门户  App Logic
   数据层直连 ERPNext REST API（经同域代理 /api → ERPNext）
   ============================================================ */
"use strict";
/* IIFE 隔离：避免 $ 等标识符污染全局（与 Frappe 的 jQuery 冲突），
   仅导出内联 onclick 依赖的少量函数 */
(function() {

/* 站点外壳（Frappe Web Page 容器）就绪后调用 frappe.highlight_code_blocks()，
   其内部经由已弃用的 hljs.initHighlighting() 输出控制台告警。
   时序：本脚本先执行，但后加载的 frappe-web.bundle 会把该方法赋回原实现，
   而 page-change（真正调用点）在 bundle 内 jQuery 的 ready 之后才触发——
   原生 DOMContentLoaded 监听按注册顺序先于 jQuery ready 执行，
   因此在此刻覆写为空操作必然落在「bundle 赋值之后、page-change 调用之前」。
   本门户无任何 <pre>/<code> 代码块，空操作不影响功能 */
document.addEventListener("DOMContentLoaded", function () {
  if (window.frappe && typeof frappe.highlight_code_blocks === "function") {
    frappe.highlight_code_blocks = function () {};
  }
});

const COMPANY = "奥登科鞋业有限公司";
/* 门户专用低权限账号令牌（portal@aodengke.com，仅授门户所需的
   库存/生产/采购/销售/财务 5 个业务角色；用户管理与系统设置均
   返回 403，无法越权提级。公开页面可见，安全边界已验证） */
const PORTAL_TOKEN = "0c72b5c60d05fcc:e815d3027f553b1";
const WAREHOUSES = {
  "材料仓": "材料仓 - 奥登科",
  "半成品仓": "半成品仓 - 奥登科",
  "委外仓": "委外供应商仓 - 奥登科",
  "在制品": "在制品 - 奥登科",
  "成品仓": "成品仓 - 奥登科",
};
const WH_COLORS = { "材料仓": "#7FA8E8", "半成品仓": "#A78BFA", "委外仓": "#FFB020", "在制品": "#4FD1C5", "成品仓": "#6ED592" };

/* ---------------- API 层 ---------------- */
const API = {
  get base() { return localStorage.getItem("odk_base") || ""; },
  get token() { return localStorage.getItem("odk_token") || ""; },
  async req(method, path, body) {
    const r = await fetch(path, {
      method,
      headers: {
        "Authorization": "token " + this.token,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    let j = {};
    try { j = await r.json(); } catch (e) { /* ignore */ }
    if (r.status === 401 || r.status === 403) {
      showLogin();
      throw new Error("登录已失效，请重新登录");
    }
    if (!r.ok) {
      const msg = extractErr(j);
      throw new Error(msg || `HTTP ${r.status}`);
    }
    return j;
  },
  async list(doctype, fields, filters, limit = 100) {
    const p = new URLSearchParams();
    p.set("limit_page_length", String(limit));
    if (fields && fields.length) p.set("fields", JSON.stringify(fields));
    if (filters) p.set("filters", JSON.stringify(filters));
    const j = await this.req("GET", `/api/resource/${encodeURIComponent(doctype)}?${p}`);
    return j.data || [];
  },
  async getDoc(doctype, name) {
    const j = await this.req("GET", `/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`);
    return j.data;
  },
  async post(doctype, data) {
    const j = await this.req("POST", `/api/resource/${encodeURIComponent(doctype)}`, data);
    return j.data;
  },
  async submitDoc(doctype, name) {
    /* frappe.client.submit 要求传完整 {doc}，不能只传 doctype+name */
    const doc = await this.getDoc(doctype, name);
    const j = await this.req("POST", "/api/method/frappe.client.submit", { doc });
    return j.message;
  },
  async method(path, args) {
    const j = await this.req("POST", `/api/method/${path}`, args || {});
    return j;
  },
};

function extractErr(j) {
  try {
    const raw = j && j._server_messages;
    if (typeof raw === "string") {
      const list = JSON.parse(raw);
      const d = list.length ? JSON.parse(list[0]) : null;
      if (d) return d.message || "";
    }
  } catch (e) { /* ignore */ }
  return (j && (j.exception || j.error || j.message)) || "";
}

/* ---------------- 工具 ---------------- */
const $ = (s, p = document) => p.querySelector(s);
const $$ = (s, p = document) => [...p.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtNum = (n, d = 0) => (n === null || n === undefined) ? "-" : Number(n).toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtMoney = (n) => "¥" + fmtNum(n, 2);
const fmtDate = (s) => s ? String(s).slice(0, 10) : "-";
const DS = (docstatus) => docstatus === 1 ? "已提交" : docstatus === 2 ? "已取消" : "草稿";

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (isErr ? " err" : "");
  t.hidden = false;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.hidden = true; }, 3200);
}
function skeleton(rows = 5) {
  return `<div class="loading-block">${"<div class='skel'></div>".repeat(rows)}</div>`;
}
function statusPill(status, docstatus) {
  const s = String(status || "");
  let cls = "draft", txt = DS(docstatus);
  if (/Completed|Paid|Submitted|Received|Received and Billed|Delivered and Billed/.test(s)) { cls = "ok"; txt = s; }
  else if (/In Process|Partially|To Deliver|To Bill|Open|Ordered/.test(s)) { cls = "run"; txt = s; }
  else if (/Unpaid|Draft|Not Started|Pending|To Bill/.test(s)) { cls = "wait"; txt = s; }
  else if (s) { cls = "run"; txt = s; }
  return `<span class="pill ${cls}">${esc(txt)}</span>`;
}
function openERP(doctype, name) {
  const base = localStorage.getItem("odk_base") || "";
  if (base) window.open(`${base}/app/${encodeURIComponent(doctype.toLowerCase().replace(/ /g, "-"))}/${encodeURIComponent(name)}`, "_blank");
}

/* ---------------- 登录 ---------------- */
function showLogin() {
  localStorage.removeItem("odk_token");
  $("#app-view").hidden = true;
  $("#login-view").style.display = "grid";
  $("#login-base").value = $("#login-base").value || (location.origin.startsWith("http") ? location.origin : "");
  /* 自动填入门户专用低权限令牌，直接点登录即可 */
  if (!$("#login-token").value) {
    $("#login-token").value = PORTAL_TOKEN;
    $("#login-token").type = "text";
  }
}
async function doLogin() {
  const base = $("#login-base").value.trim();
  const token = $("#login-token").value.trim();
  const err = $("#login-err");
  err.textContent = "";
  if (!token || !token.includes(":")) { err.textContent = "请输入正确的令牌格式（api_key:api_secret）"; return; }
  $("#login-btn").textContent = "验证中…";
  try {
    // base 用于展示，API 走同域代理 /api；禁用缓存避免命中旧身份响应
    const j = await fetch("/api/method/frappe.auth.get_logged_user", {
      headers: { "Authorization": "token " + token, "Accept": "application/json" },
      cache: "no-store",
    });
    if (!j.ok) { const e = await j.json().catch(() => ({})); throw new Error(extractErr(e) || "令牌无效"); }
    const user = (await j.json()).message;
    localStorage.setItem("odk_token", token);
    localStorage.setItem("odk_base", base || location.origin);
    localStorage.setItem("odk_user", user || "Administrator");
    enterApp();
  } catch (e) {
    err.textContent = "登录失败：" + e.message;
  } finally {
    $("#login-btn").textContent = "登 录";
  }
}
function enterApp() {
  $("#login-view").style.display = "none";
  $("#app-view").hidden = false;
  const u = localStorage.getItem("odk_user") || "Administrator";
  $("#tnav-user-name").textContent = u === "Administrator" ? "系统管理员" : u;
  $("#tnav-user-role").textContent = u;
  if (!location.hash) history.replaceState(null, "", "#/dashboard");
  render();
}

/* ---------------- 路由 ---------------- */
const TITLES = {
  dashboard: "工作台", orders: "指令单中心", purchase: "采购管理", subcontract: "委外加工",
  production: "生产制造", warehouse: "仓库管理", scan: "扫码出入库", finance: "应付对账", flow: "流程图中心",
};
const PAGES = {};
function currentRoute() {
  const h = location.hash.replace(/^#\//, "") || "dashboard";
  return TITLES[h] ? h : "dashboard";
}
let renderSeq = 0;
async function render() {
  const seq = ++renderSeq;
  const page = currentRoute();
  document.title = TITLES[page] + " · 奥登科鞋业智造协同平台";
  $$(".tnav a").forEach(a => a.classList.toggle("active", a.dataset.page === page));
  const box = $("#page");
  box.innerHTML = skeleton(8);
  try {
    await PAGES[page](box);
    if (seq !== renderSeq) return; /* 已切换到其他页面，丢弃迟到渲染 */
  } catch (e) {
    if (seq !== renderSeq) return;
    box.innerHTML = `<div class="card card-bd empty"><svg class="ic"><use href="#i-chip"/></svg><b>加载失败</b><p>${esc(e.message)}</p></div>`;
  }
}
window.addEventListener("hashchange", render);
$("#btn-logout").addEventListener("click", () => { showLogin(); });
$("#login-btn").addEventListener("click", doLogin);
$("#login-token").addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });

/* ---------------- 链路构建（指令单穿透） ---------------- */
const CHAIN_STEPS = [
  { key: "so", label: "接单", doctype: "Sales Order", name: "销售订单" },
  { key: "pp", label: "计划", doctype: "Production Plan", name: "生产计划" },
  { key: "mr", label: "MRP", doctype: "Material Request", name: "物料申请" },
  { key: "wo", label: "工单", doctype: "Work Order", name: "生产工单" },
  { key: "po", label: "采购", doctype: "Purchase Order", name: "采购订单", multi: true },
  { key: "pr", label: "收料", doctype: "Purchase Receipt", name: "采购收货", multi: true },
  { key: "sco", label: "委外", doctype: "Subcontracting Order", name: "委外订单" },
  { key: "se_out", label: "发料", doctype: "Stock Entry", name: "委外发料", multi: true },
  { key: "scr", label: "帮面", doctype: "Subcontracting Receipt", name: "委外收货", multi: true },
  { key: "se_in", label: "领料", doctype: "Stock Entry", name: "工单领料", multi: true },
  { key: "jc", label: "报工", doctype: "Job Card", name: "MES 报工", multi: true },
  { key: "se_fg", label: "入库", doctype: "Stock Entry", name: "完工入库" },
  { key: "pi", label: "应付", doctype: "Purchase Invoice", name: "应付发票", multi: true },
  { key: "pe", label: "付款", doctype: "Payment Entry", name: "付款单", multi: true },
];

async function buildChain(fo) {
  const out = { fo, steps: {} };
  // 1) 按 FO 直接查（带 custom_factory_order_no 的单据）
  const f = [["custom_factory_order_no", "=", fo]];
  const [sos, wos, mrs, pos, scos, ses, jcs] = await Promise.all([
    API.list("Sales Order", ["name", "customer", "transaction_date", "grand_total", "docstatus", "status"], f),
    API.list("Work Order", ["name", "production_item", "qty", "produced_qty", "docstatus", "status", "production_plan"], f),
    API.list("Material Request", ["name", "transaction_date", "docstatus", "status"], f),
    API.list("Purchase Order", ["name", "supplier", "transaction_date", "grand_total", "docstatus", "status"], f),
    API.list("Subcontracting Order", ["name", "supplier", "transaction_date", "docstatus", "status"], f),
    API.list("Stock Entry", ["name", "purpose", "posting_date", "docstatus", "stock_entry_type"], f),
    API.list("Job Card", ["name", "operation", "workstation", "total_completed_qty", "for_quantity", "docstatus", "status"], f),
  ]);
  out.steps.so = sos.map(d => ({ ...d, _dt: "Sales Order" }));
  out.steps.wo = wos.map(d => ({ ...d, _dt: "Work Order" }));
  out.steps.mr = mrs.map(d => ({ ...d, _dt: "Material Request" }));
  out.steps.po = pos.map(d => ({ ...d, _dt: "Purchase Order" }));
  out.steps.sco = scos.map(d => ({ ...d, _dt: "Subcontracting Order" }));
  out.steps.jc = jcs.map(d => ({ ...d, _dt: "Job Card" }));

  // 2) Stock Entry 按 purpose 分组
  out.steps.se_out = ses.filter(d => d.purpose === "Send to Subcontractor").map(d => ({ ...d, _dt: "Stock Entry" }));
  out.steps.se_in = ses.filter(d => d.purpose === "Material Transfer for Manufacture").map(d => ({ ...d, _dt: "Stock Entry" }));
  out.steps.se_fg = ses.filter(d => d.purpose === "Manufacture").map(d => ({ ...d, _dt: "Stock Entry" }));

  // 3) 推导：生产计划（由工单反查）
  const ppName = out.steps.wo[0]?.production_plan;
  if (ppName) {
    try {
      const pp = await API.getDoc("Production Plan", ppName);
      out.steps.pp = [{ ...pp, name: pp.name, _dt: "Production Plan" }];
    } catch (e) { /* skip */ }
  }

  // 4) 推导：采购收货（items.purchase_order ∈ PO）
  const poNames = new Set(out.steps.po.map(d => d.name));
  if (poNames.size) {
    const prs = await API.list("Purchase Receipt", ["name", "supplier", "posting_date", "docstatus", "status", "grand_total"], [["docstatus", "!=", 2]], 100);
    const matched = [];
    for (const pr of prs) {
      const full = await API.getDoc("Purchase Receipt", pr.name);
      if ((full.items || []).some(it => poNames.has(it.purchase_order))) matched.push({ ...pr, _dt: "Purchase Receipt" });
    }
    out.steps.pr = matched;
  }

  // 5) 推导：委外收货（subcontracting_order ∈ SCO）
  const scoNames = new Set(out.steps.sco.map(d => d.name));
  if (scoNames.size) {
    const scrs = await API.list("Subcontracting Receipt", ["name", "supplier", "posting_date", "docstatus", "status"], [["docstatus", "!=", 2]], 100);
    const matched = [];
    for (const scr of scrs) {
      const full = await API.getDoc("Subcontracting Receipt", scr.name);
      if ((full.items || []).some(it => scoNames.has(it.subcontracting_order))) matched.push({ ...scr, _dt: "Subcontracting Receipt" });
    }
    out.steps.scr = matched;
  }

  // 6) 推导：应付发票（关联 PO / PR / SCR）
  const prNames = new Set((out.steps.pr || []).map(d => d.name));
  const scrNames = new Set((out.steps.scr || []).map(d => d.name));
  if (prNames.size || poNames.size) {
    const pis = await API.list("Purchase Invoice", ["name", "supplier", "posting_date", "grand_total", "docstatus", "status"], [["docstatus", "!=", 2]], 100);
    const matched = [];
    for (const pi of pis) {
      const full = await API.getDoc("Purchase Invoice", pi.name);
      const hit = (full.items || []).some(it =>
        (it.purchase_order && poNames.has(it.purchase_order)) ||
        (it.purchase_receipt && prNames.has(it.purchase_receipt)) ||
        (it.subcontracting_receipt && scrNames.has(it.subcontracting_receipt)));
      if (hit) matched.push({ ...pi, _dt: "Purchase Invoice" });
    }
    out.steps.pi = matched;
  }

  // 7) 推导：付款单（references ∈ PI）
  const piNames = new Set((out.steps.pi || []).map(d => d.name));
  if (piNames.size) {
    const pes = await API.list("Payment Entry", ["name", "party", "posting_date", "paid_amount", "docstatus", "status"], [["docstatus", "!=", 2], ["party_type", "=", "Supplier"]], 100);
    const matched = [];
    for (const pe of pes) {
      const full = await API.getDoc("Payment Entry", pe.name);
      if ((full.references || []).some(r => piNames.has(r.reference_name))) matched.push({ ...pe, _dt: "Payment Entry" });
    }
    out.steps.pe = matched;
  }
  return out;
}

function chainStepState(step) {
  const docs = step.docs || [];
  if (!docs.length) return "todo";
  if (docs.some(d => d.docstatus === 0)) return "run";
  return "done";
}

/* 统一页面头部（渐变图标块 + 标题 + 操作区） */
function pageHeader(iconId, title, sub, right = "") {
  return `<div class="page-hd">
    <div class="ph-l">
      <span class="ph-ic"><svg><use href="#${iconId}"/></svg></span>
      <h2>${title}<small>${sub}</small></h2>
    </div>
    <div class="ph-r">${right}</div>
  </div>`;
}

/* ---------------- 抽屉 ---------------- */
function closeDrawer() { $$(".drawer,.drawer-mask").forEach(el => el.remove()); }
function openChainDrawer(fo) {
  closeDrawer();
  const mask = document.createElement("div");
  mask.className = "drawer-mask";
  mask.addEventListener("click", closeDrawer);
  document.body.appendChild(mask);
  const d = document.createElement("div");
  d.className = "drawer";
  d.innerHTML = `
    <div class="drawer-hd">
      <h3>指令单 <span class="mono">${esc(fo)}</span> 全流程链路<small>点击单号可在 ERPNext 中打开原单</small></h3>
      <button class="drawer-x">✕</button>
    </div>
    <div class="drawer-bd"><div class="loading-block">${"<div class='skel'></div>".repeat(6)}</div></div>`;
  document.body.appendChild(d);
  $(".drawer-x", d).addEventListener("click", closeDrawer);
  buildChain(fo).then(chain => {
    const bd = $(".drawer-bd", d);
    bd.innerHTML = `<div class="chain">` + CHAIN_STEPS.map(st => {
      const docs = chain.steps[st.key] || [];
      const cls = chainStepState({ docs });
      const rows = docs.length ? docs.map(x => `
        <div class="cn-row">
          <b>${esc(st.name)}</b>
          <button class="btn-sm ghost mono" data-dt="${esc(x._dt)}" data-name="${esc(x.name)}">${esc(x.name)}</button>
          ${x.docstatus === 1 ? '<span class="pill ok">已提交</span>' : '<span class="pill wait">草稿</span>'}
        </div>
        <small>${esc(x.supplier || x.customer || x.purpose || st.name)}${x.grand_total ? " · " + fmtMoney(x.grand_total) : ""}${x.qty ? " · " + fmtNum(x.qty) + " 双" : ""}</small>
      `).join("") : `<b>${esc(st.name)}</b><small>尚无单据</small>`;
      return `<div class="chain-node ${cls}">${rows}</div>`;
    }).join("") + `</div>`;
    $$("button[data-dt]", bd).forEach(b =>
      b.addEventListener("click", () => openERP(b.dataset.dt, b.dataset.name)));
  }).catch(e => {
    $(".drawer-bd", d).innerHTML = `<div class="empty">链路加载失败：${esc(e.message)}</div>`;
  });
}
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDrawer(); });

/* ---------------- 开单（在门户内直接创建业务单据） ---------------- */
const today = () => new Date().toISOString().slice(0, 10);
const plusDays = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const PAY_FROM = "现金 - 奥登科";      /* 付款账户 */
const PAY_TO = "债权人 - 奥登科";      /* 应付账款科目 */

/* 下拉数据（惰性缓存） */
const PICKS = {};
async function pick(key, doctype, fields, filters, labelFn) {
  if (!PICKS[key]) {
    const rows = await API.list(doctype, fields, filters, 200);
    PICKS[key] = rows.map(r => ({ v: r[fields[0]], t: labelFn(r) }));
  }
  return PICKS[key];
}
const pickCustomers = () => pick("cust", "Customer", ["name"], [], r => r.name);
const pickSuppliers = (subOnly) => pick(subOnly ? "sup_sub" : "sup_all", "Supplier",
  ["name", "supplier_group"], subOnly ? [["supplier_group", "=", "委外加工厂"]] : [],
  r => `${r.name}（${r.supplier_group || "供应商"}）`);
const pickFG = () => pick("fg", "Item", ["item_code", "item_name", "stock_uom"],
  [["item_code", "like", "FG-%"], ["has_variants", "=", 0]], r => `${r.item_code} ${r.item_name || ""}`);
const pickMaterials = () => pick("mat", "Item", ["item_code", "item_name", "stock_uom"],
  [["item_code", "like", "M-%"]], r => `${r.item_code} ${r.item_name || ""}`);
const pickServices = () => pick("svc", "Item", ["item_code", "item_name", "stock_uom"],
  [["item_code", "like", "SVC-%"]], r => `${r.item_code} ${r.item_name || ""}`);
const pickSemiFG = () => pick("sfg", "Item", ["item_code", "item_name", "stock_uom"],
  [["item_code", "like", "SF-%"]], r => `${r.item_code} ${r.item_name || ""}`);

/* 表单字段定义：{key,label,type,required,def,full,ph} */
const NEW_DOC_FIELDS = {
  so: [
    { key: "customer", label: "客户", type: "select", required: 1, src: pickCustomers },
    { key: "fo_no", label: "工厂指令单号", type: "text", required: 1, ph: "如 FO-20261005-01（本厂编号）" },
    { key: "item_code", label: "成品款号", type: "select", required: 1, src: pickFG },
    { key: "qty", label: "订单数量（双）", type: "number", required: 1, def: 100 },
    { key: "rate", label: "销售单价（元/双）", type: "number", ph: "留空按价目表自动取价" },
    { key: "delivery_date", label: "客户交期", type: "date", def: plusDays(30) },
  ],
  po: [
    { key: "supplier", label: "供应商", type: "select", required: 1, src: () => pickSuppliers(false) },
    { key: "item_code", label: "采购物料", type: "select", required: 1, src: pickMaterials },
    { key: "qty", label: "采购数量", type: "number", required: 1, def: 100 },
    { key: "rate", label: "采购单价（元）", type: "number", required: 1 },
    { key: "schedule_date", label: "到货日期", type: "date", def: plusDays(10) },
    { key: "fo_no", label: "关联指令单号", type: "text", ph: "可选，用于链路穿透归集" },
  ],
  sub: [
    { key: "supplier", label: "委外加工厂", type: "select", required: 1, src: () => pickSuppliers(true) },
    { key: "svc_item", label: "加工服务项目", type: "select", required: 1, src: pickServices },
    { key: "fg_item", label: "加工产出（生成成品）", type: "select", required: 1, src: pickSemiFG },
    { key: "qty", label: "加工数量", type: "number", required: 1, def: 200 },
    { key: "rate", label: "加工单价（元）", type: "number", required: 1 },
    { key: "schedule_date", label: "交回日期", type: "date", def: plusDays(15) },
  ],
  pay: [
    { key: "party", label: "付款对象（供应商）", type: "select", required: 1, src: () => pickSuppliers(false) },
    { key: "paid_amount", label: "付款金额（元）", type: "number", required: 1 },
    { key: "reference_no", label: "付款摘要 / 流水号", type: "text", required: 1, ph: "如 10 月针车加工费", full: 1 },
  ],
};
const NEW_DOC_META = {
  so: { icon: "i-order", title: "新建指令单", sub: "客户接单 → 生成销售订单并提交生效" },
  po: { icon: "i-buy", title: "新建采购单", sub: "向材料供应商下达采购订单并提交生效" },
  sub: { icon: "i-sub", title: "新建委外单", sub: "一步完成：委外采购单 + 委外加工单，均自动提交" },
  pay: { icon: "i-fin", title: "登记付款", sub: "现金账户向供应商付款，提交后自动生成财务分录" },
};

/* 各类型单据的创建实现，返回 [类型名, 单号, ...] */
const NEW_DOC_BUILDERS = {
  async so(v) {
    const items = [{ item_code: v.item_code, qty: Number(v.qty) }];
    if (v.rate) items[0].rate = Number(v.rate);
    const d = await API.post("Sales Order", {
      company: COMPANY, customer: v.customer,
      transaction_date: today(), delivery_date: v.delivery_date,
      custom_factory_order_no: v.fo_no, items,
    });
    await API.submitDoc("Sales Order", d.name);
    return ["销售订单", d.name];
  },
  async po(v) {
    const d = await API.post("Purchase Order", {
      company: COMPANY, supplier: v.supplier,
      transaction_date: today(), schedule_date: v.schedule_date,
      custom_factory_order_no: v.fo_no || undefined,
      items: [{ item_code: v.item_code, qty: Number(v.qty), rate: Number(v.rate) }],
    });
    await API.submitDoc("Purchase Order", d.name);
    return ["采购订单", d.name];
  },
  async sub(v) {
    const qty = Number(v.qty), rate = Number(v.rate), amount = qty * rate;
    /* ① 委外采购订单（服务项目 + 生成成品） */
    const po = await API.post("Purchase Order", {
      company: COMPANY, supplier: v.supplier, is_subcontracted: 1,
      transaction_date: today(), schedule_date: v.schedule_date,
      items: [{ item_code: v.svc_item, qty, rate, fg_item: v.fg_item, fg_item_qty: qty, warehouse: WAREHOUSES["半成品仓"] }],
    });
    await API.submitDoc("Purchase Order", po.name);
    /* ② 按产出查默认 BOM，组装委外加工单 */
    const boms = await API.list("BOM", ["name"], [["item", "=", v.fg_item], ["is_active", "=", 1]], 3);
    const bom = (boms.find(b => /-001$/.test(b.name)) || boms[0] || {}).name;
    const poDoc = await API.getDoc("Purchase Order", po.name);
    const poi = (poDoc.items || [])[0]?.name;
    const sc = await API.post("Subcontracting Order", {
      company: COMPANY, supplier: v.supplier,
      transaction_date: today(), purchase_order: po.name,
      supplier_warehouse: WAREHOUSES["委外仓"],
      service_items: [{ item_code: v.svc_item, qty, rate, amount, fg_item: v.fg_item, fg_item_qty: qty, purchase_order_item: poi }],
      items: [{ item_code: v.fg_item, qty, rate, amount, warehouse: WAREHOUSES["半成品仓"],
                bom, schedule_date: v.schedule_date, service_cost_per_qty: rate,
                subcontracting_conversion_factor: 1, purchase_order_item: poi }],
    });
    await API.submitDoc("Subcontracting Order", sc.name);
    return ["委外加工单", sc.name, "委外采购单", po.name];
  },
  async pay(v) {
    const amt = Number(v.paid_amount);
    const d = await API.post("Payment Entry", {
      company: COMPANY, payment_type: "Pay",
      party_type: "Supplier", party: v.party,
      paid_from: PAY_FROM, paid_from_account_currency: "CNY",
      paid_to: PAY_TO, paid_to_account_currency: "CNY",
      paid_amount: amt, received_amount: amt,
      source_exchange_rate: 1, target_exchange_rate: 1,
      reference_no: v.reference_no, reference_date: today(),
    });
    await API.submitDoc("Payment Entry", d.name);
    return ["付款单", d.name];
  },
};

/* 开单抽屉 */
function openNewDoc(type) {
  const meta = NEW_DOC_META[type], fields = NEW_DOC_FIELDS[type];
  if (!meta) return;
  closeDrawer();
  const mask = document.createElement("div");
  mask.className = "drawer-mask";
  mask.addEventListener("click", closeDrawer);
  document.body.appendChild(mask);
  const d = document.createElement("div");
  d.className = "drawer";
  d.innerHTML = `
    <div class="drawer-hd">
      <h3>${meta.title}<small>${meta.sub}</small></h3>
      <button class="drawer-x">✕</button>
    </div>
    <div class="drawer-bd"><div class="loading-block">${"<div class='skel'></div>".repeat(5)}</div></div>`;
  document.body.appendChild(d);
  $(".drawer-x", d).addEventListener("click", closeDrawer);

  Promise.all(fields.map(f => f.type === "select" ? f.src() : null)).then(srcs => {
    const bd = $(".drawer-bd", d);
    bd.innerHTML = `<div class="nd-form">
      ${fields.map((f, i) => `
        <div class="fd-field ${f.full ? "full" : ""}">
          <label>${f.label}${f.required ? ' <i class="req">*</i>' : ""}</label>
          ${f.type === "select"
            ? `<select id="nf-${f.key}">${(srcs[i] || []).map(o => `<option value="${esc(o.v)}">${esc(o.t)}</option>`).join("")}</select>`
            : `<input id="nf-${f.key}" type="${f.type}" value="${f.def || ""}" placeholder="${f.ph || ""}" ${f.type === "number" ? 'min="0" step="0.01"' : ""}>`}
        </div>`).join("")}
      <div class="fd-actions full">
        <button class="btn-sm ghost" id="nf-cancel">取 消</button>
        <button class="btn-amber" id="nf-submit">${meta.title}</button>
      </div>
    </div>`;
    $("#nf-cancel", d).addEventListener("click", closeDrawer);
    $("#nf-submit", d).addEventListener("click", async () => {
      const btn = $("#nf-submit", d);
      const v = {};
      for (const f of fields) {
        const el = $(`#nf-${f.key}`, d);
        v[f.key] = String(el.value || "").trim();
        if (f.required && !v[f.key]) { toast(`请填写「${f.label}」`, true); el.focus(); return; }
      }
      btn.disabled = true; btn.textContent = "创建中…";
      try {
        const parts = await NEW_DOC_BUILDERS[type](v);
        closeDrawer();
        let msg = parts[0] + " " + parts[1] + " 已创建并提交 ✓";
        if (parts.length > 2) msg += "（同时生成 " + parts[2] + " " + parts[3] + "）";
        toast(msg);
        render(); /* 刷新当前页列表，让新单据立即可见 */
      } catch (e) {
        toast("创建失败：" + (e.message || "请检查填写内容"), true);
        btn.disabled = false; btn.textContent = meta.title;
      }
    });
    const firstInput = $(".fd-field input, .fd-field select", d);
    if (firstInput) firstInput.focus();
  }).catch(e => {
    $(".drawer-bd", d).innerHTML = `<div class="empty">数据加载失败：${esc(e.message)}</div>`;
  });
}

/* 列表内草稿一键提交 */
async function doSubmitDoc(dt, name) {
  toast("正在提交 " + name + " …");
  try {
    await API.submitDoc(dt, name);
    toast(dt === "Sales Order" ? "指令单 " + name + " 已提交生效 ✓" : name + " 已提交生效 ✓");
    render();
  } catch (e) {
    toast("提交失败：" + (e.message || "请检查单据"), true);
  }
}
window.openNewDoc = openNewDoc;   /* 供页面内联按钮调用 */
window.doSubmitDoc = doSubmitDoc;

/* ---------------- 工作台 ---------------- */
PAGES.dashboard = async function (box) {
  const [sos, wos, pis, bins, drafts] = await Promise.all([
    API.list("Sales Order", ["name", "customer", "transaction_date", "grand_total", "docstatus", "status", "custom_factory_order_no"], [["docstatus", "=", 1]], 50),
    API.list("Work Order", ["name", "production_item", "qty", "produced_qty", "status", "docstatus"], [["docstatus", "=", 1]], 50),
    API.list("Purchase Invoice", ["name", "supplier", "grand_total", "status", "docstatus"], [["docstatus", "=", 1]], 100),
    API.list("Bin", ["item_code", "warehouse", "actual_qty"], [["actual_qty", ">", 0]], 200),
    API.list("Sales Order", ["name", "status"], [["docstatus", "=", 0]], 20),
  ]);
  const activeSO = sos.filter(s => !/Completed/.test(s.status || ""));
  const activeWO = wos.filter(w => !/Completed/.test(w.status || ""));
  const unpaid = pis.filter(p => !/Paid$/.test(p.status || "") || /Overdue|Unpaid|Partly/.test(p.status || ""));
  const unpaidAmt = unpaid.reduce((a, b) => a + (b.grand_total || 0), 0);
  const fgQty = bins.filter(b => b.warehouse === WAREHOUSES["成品仓"]).reduce((a, b) => a + b.actual_qty, 0);

  const now = new Date();
  const hour = now.getHours();
  const greet = hour < 9 ? "早上好" : hour < 12 ? "中午好" : hour < 18 ? "下午好" : "晚上好";
  const dateStr = now.toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" });
  const user = localStorage.getItem("odk_user") || "Administrator";
  const displayName = user === "Administrator" ? "系统管理员" : user;

  // 最近指令单链路进度
  const fo = sos[0]?.custom_factory_order_no || activeSO[0]?.custom_factory_order_no;
  let flowbarHTML = "";
  if (fo) {
    const chain = await buildChain(fo);
    const doneSteps = CHAIN_STEPS.filter(st => chainStepState({ docs: chain.steps[st.key] }) === "done").length;
    flowbarHTML = `
      <div class="card" style="margin-bottom:16px">
        <div class="card-hd">
          <h3>指令单 ${esc(fo)} · 全流程进度</h3>
          <div class="fc-sum">
            <b class="fc-num"><i>${doneSteps}</i> / ${CHAIN_STEPS.length}</b>
            ${doneSteps === CHAIN_STEPS.length ? '<span class="pill ok">已全部完成</span>' : '<span class="pill wait">进行中</span>'}
            <button class="btn-sm amber" onclick="openChainDrawer('${esc(fo)}')">查看完整链路</button>
          </div>
        </div>
        <div class="card-bd"><div class="flowbar">${CHAIN_STEPS.map(st => {
          const cls = chainStepState({ docs: chain.steps[st.key] });
          return `<div class="fb-step"><div class="fb-chip ${cls === "done" ? "done" : cls === "run" ? "run" : ""}">
            <div class="fb-dot">${cls === "done" ? "✓" : esc(st.label)}</div><b>${esc(st.label)}</b></div><div class="fb-arrow">→</div></div>`;
        }).join("")}</div></div>
      </div>`;
  }

  // 待办
  const todoRows = drafts.map(d => `
    <div class="todo-item"><div class="td-ic warn"><svg class="ic"><use href="#i-order"/></svg></div>
      <div><b>销售订单 ${esc(d.name)} 未提交</b><span>接单后请尽快提交以启动 MRP 运算</span></div>
      <button class="btn-sm" onclick="openERP('Sales Order','${esc(d.name)}')">去处理</button></div>`).join("") ||
    '<div class="empty" style="padding:20px">暂无待办，一切就绪</div>';

  // 库存概览
  const whRows = Object.keys(WAREHOUSES).map(k => {
    const total = bins.filter(b => b.warehouse === WAREHOUSES[k]).reduce((a, b) => a + b.actual_qty, 0);
    const cnt = bins.filter(b => b.warehouse === WAREHOUSES[k] && b.actual_qty > 0).length;
    return `<div class="wh-chip"><span class="dot" style="background:${WH_COLORS[k]}"></span>
      <b>${k}<small style="color:var(--sub);font-weight:400;margin-left:6px">${cnt} 种料件</small></b>
      <span class="qty">${fmtNum(total)}</span></div>`;
  }).join("");

  box.innerHTML = `
    <div class="hero-banner">
      <div class="hb-l">
        <h2>${greet}，${esc(displayName)}</h2>
        <p>${dateStr} · 鞋业代工全流程运转正常，数据实时同步自 ERPNext</p>
      </div>
      <div class="hb-r">
        <div class="hb-chip"><b>${fmtNum(sos.length)}</b><span>累计接单</span></div>
        <div class="hb-chip"><b>${fmtNum(fgQty)}</b><span>成品库存（双）</span></div>
        <div class="hb-chip"><b>${fmtNum(unpaidAmt, 0)}</b><span>未结货款（元）</span></div>
      </div>
    </div>
    <div class="grid g4" style="margin-bottom:16px">
      <div class="card stat-card">
        <span class="stat-no">01</span>
        <span class="stat-ic blue"><svg><use href="#i-order"/></svg></span>
        <div class="stat-body"><div class="stat-label">进行中指令单</div>
          <div class="stat-value">${fmtNum(activeSO.length)}<small>单</small></div>
          <div class="stat-foot">累计接单 ${sos.length} 单</div></div>
      </div>
      <div class="card stat-card">
        <span class="stat-no">02</span>
        <span class="stat-ic cyan"><svg><use href="#i-mfg"/></svg></span>
        <div class="stat-body"><div class="stat-label">在产工单</div>
          <div class="stat-value">${fmtNum(activeWO.reduce((a, b) => a + (b.qty || 0), 0))}<small>双</small></div>
          <div class="stat-foot">${activeWO.length} 张工单生产中</div></div>
      </div>
      <div class="card stat-card">
        <span class="stat-no">03</span>
        <span class="stat-ic amber"><svg><use href="#i-fin"/></svg></span>
        <div class="stat-body"><div class="stat-label">待付货款</div>
          <div class="stat-value">${fmtNum(unpaidAmt / 10000, 1)}<small>万元</small></div>
          <div class="stat-foot">${unpaid.length} 张发票待付</div></div>
      </div>
      <div class="card stat-card">
        <span class="stat-no">04</span>
        <span class="stat-ic green"><svg><use href="#i-wh"/></svg></span>
        <div class="stat-body"><div class="stat-label">成品仓库存</div>
          <div class="stat-value">${fmtNum(fgQty)}<small>双</small></div>
          <div class="stat-foot">即时库存快照</div></div>
      </div>
    </div>
    ${flowbarHTML}
    <div class="grid g2">
      <div class="card"><div class="card-hd"><h3>待办事项</h3><span class="pill draft">共 ${drafts.length} 条</span></div>
        <div class="card-bd">${todoRows}</div></div>
      <div class="card"><div class="card-hd"><h3>库存概览</h3><button class="btn-sm ghost" onclick="location.hash='#/warehouse'">仓库明细</button></div>
        <div class="card-bd">${whRows}</div></div>
    </div>`;
};

/* ---------------- 指令单中心 ---------------- */
PAGES.orders = async function (box) {
  const sos = await API.list("Sales Order",
    ["name", "customer", "transaction_date", "grand_total", "docstatus", "status", "custom_factory_order_no", "transaction_date"],
    [["docstatus", "!=", 2]], 100);
  // 汇总每单的明细（款号与数量）
  const rows = await Promise.all(sos.map(async so => {
    const full = await API.getDoc("Sales Order", so.name);
    const items = (full.items || []).map(i => `${i.item_code} × ${fmtNum(i.qty)}`).join("<br>");
    return { ...so, items };
  }));
  box.innerHTML = `
    ${pageHeader("i-order", "指令单中心", "以工厂指令单号为主线，点击行查看全流程链路穿透",
      `<button class="btn-amber" onclick="openNewDoc('so')">＋ 新建指令单</button><span class="pill run">共 ${rows.length} 单</span>`)}
    <div class="card">
      <div class="card-hd"><h3>订单列表</h3><span style="font-size:12.5px;color:var(--sub)">点击任意行展开链路抽屉</span></div>
      <table class="tbl">
        <thead><tr><th>指令单号</th><th>销售订单</th><th>客户</th><th>款号明细</th><th>订单金额</th><th>日期</th><th>状态</th><th></th></tr></thead>
        <tbody>${rows.map(so => `
          <tr style="cursor:pointer" onclick="openChainDrawer('${esc(so.custom_factory_order_no || so.name)}')">
            <td><b class="mono" style="color:var(--amber)">${esc(so.custom_factory_order_no || "—")}</b></td>
            <td class="mono">${esc(so.name)}</td>
            <td>${esc(so.customer)}</td>
            <td style="font-size:12.5px;color:var(--sub)">${so.items}</td>
            <td class="num">${fmtMoney(so.grand_total)}</td>
            <td class="num">${fmtDate(so.transaction_date)}</td>
            <td>${statusPill(so.status, so.docstatus)}</td>
            <td>${so.docstatus === 0
              ? `<button class="btn-sm amber" onclick="event.stopPropagation();doSubmitDoc('Sales Order','${esc(so.name)}')">提交</button>`
              : `<button class="btn-sm ghost" onclick="event.stopPropagation();openERP('Sales Order','${esc(so.name)}')">原单</button>`}</td>
          </tr>`).join("") || `<tr><td colspan="8" class="empty">暂无订单，点右上角「＋ 新建指令单」开始接单</td></tr>`}
        </tbody>
      </table>
    </div>`;
};

/* ---------------- 采购管理 ---------------- */
PAGES.purchase = async function (box) {
  const [pos, prs, sups] = await Promise.all([
    API.list("Purchase Order", ["name", "supplier", "transaction_date", "grand_total", "docstatus", "status", "custom_factory_order_no"], [["docstatus", "!=", 2]], 100),
    API.list("Purchase Receipt", ["name", "supplier", "posting_date", "grand_total", "docstatus", "status"], [["docstatus", "!=", 2]], 100),
    API.list("Supplier", ["name", "supplier_name", "supplier_group", "country"], [], 100),
  ]);
  box.innerHTML = `
    ${pageHeader("i-buy", "采购管理", "材料采购订单与到货收料全程跟踪",
      `<button class="btn-amber" onclick="openNewDoc('po')">＋ 新建采购单</button><span class="pill run">采购总额 ${fmtMoney(pos.reduce((a, b) => a + (b.grand_total || 0), 0))}</span>`)}
    <div class="grid g2" style="margin-bottom:14px">
      <div class="card"><div class="card-hd"><h3>供应商（${sups.length}）</h3></div><div class="card-bd" style="padding:8px 18px">
        ${sups.map(s => `<div class="wh-chip"><span class="dot" style="background:${s.supplier_group === "委外加工厂" ? "#FFB020" : "#7FA8E8"}"></span>
          <b>${esc(s.supplier_name)}<small style="color:var(--sub);font-weight:400;margin-left:6px">${esc(s.supplier_group || "")}</small></b></div>`).join("")}
      </div></div>
      <div class="card"><div class="card-hd"><h3>采购概览</h3></div><div class="card-bd">
        <div class="wh-chip"><span class="dot" style="background:#7FA8E8"></span><b>采购订单总数</b><span class="qty">${pos.length}</span></div>
        <div class="wh-chip"><span class="dot" style="background:#6ED592"></span><b>已到货收料</b><span class="qty">${prs.length}</span></div>
        <div class="wh-chip"><span class="dot" style="background:#FFB020"></span><b>采购总额</b><span class="qty">${fmtMoney(pos.reduce((a, b) => a + (b.grand_total || 0), 0))}</span></div>
      </div></div>
    </div>
    <div class="card" style="margin-bottom:14px">
      <div class="card-hd"><h3>采购订单</h3></div>
      <table class="tbl"><thead><tr><th>订单号</th><th>供应商</th><th>指令单</th><th>金额</th><th>日期</th><th>状态</th><th></th></tr></thead>
      <tbody>${pos.map(p => `<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.supplier)}</td>
        <td class="mono">${esc(p.custom_factory_order_no || "—")}</td><td class="num">${fmtMoney(p.grand_total)}</td>
        <td class="num">${fmtDate(p.transaction_date)}</td><td>${statusPill(p.status, p.docstatus)}</td>
        <td>${p.docstatus === 0
          ? `<button class="btn-sm amber" onclick="doSubmitDoc('Purchase Order','${esc(p.name)}')">提交</button>`
          : `<button class="btn-sm ghost" onclick="openERP('Purchase Order','${esc(p.name)}')">原单</button>`}</td></tr>`).join("")}
      </tbody></table>
    </div>
    <div class="card">
      <div class="card-hd"><h3>采购收货单</h3></div>
      <table class="tbl"><thead><tr><th>收货单号</th><th>供应商</th><th>金额</th><th>日期</th><th>状态</th><th></th></tr></thead>
      <tbody>${prs.map(p => `<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.supplier)}</td>
        <td class="num">${fmtMoney(p.grand_total)}</td><td class="num">${fmtDate(p.posting_date)}</td>
        <td>${statusPill(p.status, p.docstatus)}</td>
        <td><button class="btn-sm ghost" onclick="openERP('Purchase Receipt','${esc(p.name)}')">原单</button></td></tr>`).join("")}
      </tbody></table>
    </div>`;
};

/* ---------------- 委外加工 ---------------- */
PAGES.subcontract = async function (box) {
  const [scos, scrs] = await Promise.all([
    API.list("Subcontracting Order", ["name", "supplier", "transaction_date", "status", "docstatus", "custom_factory_order_no"], [["docstatus", "!=", 2]], 100),
    API.list("Subcontracting Receipt", ["name", "supplier", "posting_date", "status", "docstatus"], [["docstatus", "!=", 2]], 100),
  ]);
  const [seOut, seIn] = await Promise.all([
    API.list("Stock Entry", ["name", "purpose", "posting_date", "docstatus"], [["purpose", "=", "Send to Subcontractor"], ["docstatus", "!=", 2]], 100),
    API.list("Stock Entry", ["name", "purpose", "posting_date", "docstatus"], [["purpose", "=", "Material Transfer for Manufacture"], ["docstatus", "!=", 2]], 100),
  ]);
  box.innerHTML = `
    ${pageHeader("i-sub", "委外加工", "发料给委外厂 → 帮面收货 → 加工费结算",
      `<button class="btn-amber" onclick="openNewDoc('sub')">＋ 新建委外单</button><span class="pill run">${scos.length} 张委外订单</span>`)}
    <div class="grid g3" style="margin-bottom:14px">
      <div class="card stat-card">
        <span class="stat-ic blue"><svg><use href="#i-sub"/></svg></span>
        <div class="stat-body"><div class="stat-label">委外订单</div><div class="stat-value">${scos.length}<small>单</small></div></div>
      </div>
      <div class="card stat-card">
        <span class="stat-ic cyan"><svg><use href="#i-scan"/></svg></span>
        <div class="stat-body"><div class="stat-label">累计发料</div><div class="stat-value">${seOut.length}<small>笔</small></div></div>
      </div>
      <div class="card stat-card">
        <span class="stat-ic green"><svg><use href="#i-wh"/></svg></span>
        <div class="stat-body"><div class="stat-label">帮面到货</div><div class="stat-value">${scrs.length}<small>单</small></div></div>
      </div>
    </div>
    <div class="card" style="margin-bottom:14px">
      <div class="card-hd"><h3>委外订单（SCO）</h3></div>
      <table class="tbl"><thead><tr><th>委外单号</th><th>委外厂</th><th>指令单</th><th>日期</th><th>状态</th><th></th></tr></thead>
      <tbody>${scos.map(s => `<tr><td class="mono">${esc(s.name)}</td><td>${esc(s.supplier)}</td>
        <td class="mono">${esc(s.custom_factory_order_no || "—")}</td><td class="num">${fmtDate(s.transaction_date)}</td>
        <td>${statusPill(s.status, s.docstatus)}</td>
        <td>${s.docstatus === 0
          ? `<button class="btn-sm amber" onclick="doSubmitDoc('Subcontracting Order','${esc(s.name)}')">提交</button>`
          : `<button class="btn-sm ghost" onclick="openERP('Subcontracting Order','${esc(s.name)}')">原单</button>`}</td></tr>`).join("")}
      </tbody></table>
    </div>
    <div class="grid g2">
      <div class="card">
        <div class="card-hd"><h3>委外发料记录</h3></div>
        <table class="tbl"><thead><tr><th>发料单号</th><th>日期</th><th>状态</th></tr></thead>
        <tbody>${seOut.map(s => `<tr><td class="mono">${esc(s.name)}</td><td class="num">${fmtDate(s.posting_date)}</td>
          <td>${s.docstatus === 1 ? '<span class="pill ok">已提交</span>' : '<span class="pill wait">草稿</span>'}</td></tr>`).join("") || `<tr><td colspan="3" class="empty">暂无发料</td></tr>`}
        </tbody></table>
      </div>
      <div class="card">
        <div class="card-hd"><h3>帮面收货记录</h3></div>
        <table class="tbl"><thead><tr><th>收货单号</th><th>委外厂</th><th>日期</th><th>状态</th></tr></thead>
        <tbody>${scrs.map(s => `<tr><td class="mono">${esc(s.name)}</td><td>${esc(s.supplier)}</td>
          <td class="num">${fmtDate(s.posting_date)}</td><td>${statusPill(s.status, s.docstatus)}</td></tr>`).join("") || `<tr><td colspan="4" class="empty">暂无收货</td></tr>`}
        </tbody></table>
      </div>
    </div>`;
};

/* ---------------- 生产制造 ---------------- */
PAGES.production = async function (box) {
  const [wos, jcs] = await Promise.all([
    API.list("Work Order", ["name", "production_item", "qty", "produced_qty", "status", "docstatus", "custom_factory_order_no", "planned_start_date"], [["docstatus", "!=", 2]], 100),
    API.list("Job Card", ["name", "work_order", "operation", "workstation", "for_quantity", "total_completed_qty", "status", "docstatus"], [["docstatus", "!=", 2]], 100),
  ]);
  box.innerHTML = `
    ${pageHeader("i-mfg", "生产制造", "工单进度与 MES 工序报工", `<span class="pill run">${wos.length} 张工单</span>`)}
    <div class="grid g2" style="margin-bottom:14px">
      ${wos.map(w => {
        const pct = w.qty ? Math.round((w.produced_qty || 0) / w.qty * 100) : 0;
        const done = /Completed/.test(w.status || "");
        return `<div class="card card-bd">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <b class="mono">${esc(w.name)}</b>${statusPill(w.status, w.docstatus)}</div>
          <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--sub);margin-bottom:10px">
            <span>成品：<b style="color:var(--ink)">${esc(w.production_item)}</b></span>
            <span class="mono">指令单 ${esc(w.custom_factory_order_no || "—")}</span></div>
          <div style="height:10px;background:rgba(255,255,255,.05);border-radius:5px;overflow:hidden;margin-bottom:6px;box-shadow:inset 0 2px 4px rgba(0,0,0,.35)">
            <div style="width:${pct}%;height:100%;background:${done ? "linear-gradient(90deg,#DB8A00,#FFB020,#FFC455)" : "linear-gradient(90deg,#2AA398,#4FD1C5,#6FE0D6)"};border-radius:5px;transition:width .6s;box-shadow:0 0 12px rgba(255,176,32,.35)"></div></div>
          <div style="display:flex;justify-content:space-between;font-size:12.5px">
            <span style="color:var(--sub)">计划 <b class="num" style="color:var(--ink)">${fmtNum(w.qty)}</b> 双</span>
            <span style="color:var(--sub)">已入库 <b class="num" style="color:${done ? "#FFB020" : "#4FD1C5"}">${fmtNum(w.produced_qty || 0)}</b> 双（${pct}%）</span>
          </div>
          <div style="margin-top:10px;display:flex;gap:8px">
            <button class="btn-sm" onclick="openERP('Work Order','${esc(w.name)}')">工单详情</button>
            ${jcs.filter(j => j.work_order === w.name).map(j =>
              `<button class="btn-sm ghost" onclick="openERP('Job Card','${esc(j.name)}')">报工：${esc(j.operation)}</button>`).join("")}
          </div></div>`;
      }).join("") || `<div class="card card-bd empty">暂无工单</div>`}
    </div>
    <div class="card">
      <div class="card-hd"><h3>MES 工序报工（Job Card）</h3></div>
      <table class="tbl"><thead><tr><th>报工单号</th><th>工单</th><th>工序</th><th>工位</th><th>完成/计划</th><th>状态</th></tr></thead>
      <tbody>${jcs.map(j => `<tr><td class="mono">${esc(j.name)}</td><td class="mono">${esc(j.work_order || "-")}</td>
        <td>${esc(j.operation)}</td><td>${esc(j.workstation)}</td>
        <td class="num">${fmtNum(j.total_completed_qty || 0)} / ${fmtNum(j.for_quantity || 0)}</td>
        <td>${statusPill(j.status, j.docstatus)}</td></tr>`).join("") || `<tr><td colspan="6" class="empty">暂无报工记录</td></tr>`}
      </tbody></table>
    </div>`;
};

/* ---------------- 仓库管理 ---------------- */
PAGES.warehouse = async function (box) {
  const bins = await API.list("Bin", ["item_code", "warehouse", "actual_qty"], [["actual_qty", ">", 0]], 500);
  const rows = Object.keys(WAREHOUSES).map(k => {
    const wh = WAREHOUSES[k];
    const items = bins.filter(b => b.warehouse === wh);
    const total = items.reduce((a, b) => a + b.actual_qty, 0);
    return `<div class="card">
      <div class="card-hd"><h3>${k}</h3>
        <span style="font-family:var(--num-font);font-size:20px;font-weight:700;color:${WH_COLORS[k]}">${fmtNum(total)}</span></div>
      <div class="card-bd" style="padding:6px 18px">
        ${items.map(b => `<div class="wh-chip"><b>${esc(b.item_code)}</b><span class="qty" style="color:${WH_COLORS[k]}">${fmtNum(b.actual_qty)}</span></div>`).join("") || '<div class="empty" style="padding:16px">空仓</div>'}
      </div></div>`;
  }).join("");
  box.innerHTML = `
    ${pageHeader("i-wh", "仓库管理", "五大仓位实时库存 · 出入库请用顶部「扫码出入库」", `<button class="btn-sm amber" onclick="location.hash='#/scan'">去扫码出入库</button>`)}
    <div class="grid g3">${rows}</div>`;
};

/* ---------------- 扫码出入库 ---------------- */
let SCAN_CACHE = null;
async function loadItemsWithBarcode() {
  if (SCAN_CACHE) return SCAN_CACHE;
  const items = await API.list("Item", ["name", "item_code", "item_name", "item_group", "stock_uom"], [], 500);
  const withCodes = await Promise.all(items.map(async it => {
    const full = await API.getDoc("Item", it.name);
    return { ...it, barcodes: (full.barcodes || []).map(b => b.barcode).filter(Boolean) };
  }));
  SCAN_CACHE = withCodes;
  return withCodes;
}
function scanReset() {
  $("#scan-input").value = "";
  $("#scan-input").focus();
}
PAGES.scan = async function (box) {
  box.innerHTML = `
    ${pageHeader("i-scan", "扫码出入库", "USB 扫码枪即扫即录 · 自动创建库存调拨单并提交", `<span class="pill run">识别即建单 · 提交生效</span>`)}
    <div class="scan-layout">
      <div>
        <div class="scan-hero">
          <h2>物料条码扫描</h2>
          <p>光标聚焦输入框 → 扫描物料条码（或手动输入后回车）→ 选择方向与仓位 → 提交</p>
          <input id="scan-input" type="text" placeholder="扫描 / 输入条码，如 6901234500011" autocomplete="off">
          <div class="scan-meta">
            <span>今日扫描 <b id="scan-count">0</b> 笔</span>
            <span>状态 <b id="scan-state">待扫描</b></span>
            <span>模式 <b>库存调拨（Material Transfer）</b></span>
          </div>
        </div>
        <div class="card" id="scan-detail" style="margin-top:14px">
          <div class="card-bd empty"><svg class="ic"><use href="#i-scan"/></svg><b>等待扫描</b><p>扫描条码后此处显示物料信息与出入库表单</p></div>
        </div>
      </div>
      <div class="card scan-log">
        <div class="card-hd"><h3>本次会话记录</h3><button class="btn-sm ghost" onclick="scanClearLog()">清空</button></div>
        <div class="card-bd" id="scan-log"><div class="empty" style="padding:20px">暂无记录</div></div>
      </div>
    </div>`;
  const input = $("#scan-input");
  input.focus();
  input.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter") return;
    const code = input.value.trim();
    if (!code) return;
    await handleScan(code);
  });
};
let scanLog = [];
window.scanClearLog = () => { scanLog = []; $("#scan-count").textContent = "0"; $("#scan-log").innerHTML = '<div class="empty" style="padding:20px">暂无记录</div>'; };
async function handleScan(code) {
  const state = $("#scan-state");
  state.textContent = "识别中…";
  try {
    const items = await loadItemsWithBarcode();
    const hit = items.find(it => it.barcodes.includes(code) || it.item_code === code);
    if (!hit) {
      state.textContent = "未识别";
      toast("条码未找到对应物料：" + code, true);
      $("#scan-input").select();
      return;
    }
    state.textContent = "已识别";
    renderScanForm(hit, code);
  } catch (e) {
    state.textContent = "识别失败";
    toast(e.message, true);
  }
}
function renderScanForm(item, code) {
  const whOpts = Object.keys(WAREHOUSES).map(k => `<option value="${WAREHOUSES[k]}">${k}</option>`).join("");
  $("#scan-detail").innerHTML = `
    <div class="card-bd">
      <div class="scan-item">
        <div class="si-img"><svg class="ic"><use href="#i-shoe"/></svg></div>
        <div style="flex:1">
          <b>${esc(item.item_code)} <span style="font-weight:400;color:var(--sub)">（${esc(item.item_group || "")}）</span></b>
          <span>${esc(item.item_name || "")} · 单位 ${esc(item.stock_uom || "")} · 条码 <span class="mono">${esc(code)}</span></span>
        </div>
        <span class="pill run">已识别</span>
      </div>
      <div class="scan-row">
        <select id="scan-from">${whOpts}</select>
        <span style="align-self:center;color:var(--sub)">→</span>
        <select id="scan-to">${whOpts}</select>
        <input id="scan-qty" type="number" min="1" step="1" value="1" title="数量">
        <input id="scan-fo" type="text" placeholder="工厂指令单号（可选）" style="border:1px solid var(--line);border-radius:8px;padding:9px 12px;font-family:inherit;outline:none;min-width:150px">
        <button id="scan-submit" class="btn-amber">提交出入库</button>
      </div>
      <p style="font-size:12px;color:var(--sub);margin-top:8px">常用方向：材料入库选「材料仓→材料仓」以外的组合 — 发料给委外厂选「材料仓→委外仓」，车间领料选「半成品仓→在制品」，成品移仓选「在制品→成品仓」。</p>
    </div>`;
  $("#scan-to").selectedIndex = 1;
  $("#scan-submit").addEventListener("click", async () => {
    const from = $("#scan-from").value, to = $("#scan-to").value;
    const qty = parseFloat($("#scan-qty").value || "0");
    const fo = $("#scan-fo").value.trim();
    if (qty <= 0) return toast("数量必须大于 0", true);
    if (from === to) return toast("源仓与目标仓不能相同", true);
    const btn = $("#scan-submit");
    btn.disabled = true; btn.textContent = "提交中…";
    try {
      const doc = await API.post("Stock Entry", {
        company: COMPANY,
        purpose: "Material Transfer",
        stock_entry_type: "Material Transfer",
        from_warehouse: from,
        to_warehouse: to,
        custom_factory_order_no: fo || undefined,
        items: [{
          doctype: "Stock Entry Detail",
          item_code: item.item_code,
          s_warehouse: from,
          t_warehouse: to,
          qty,
          transfer_qty: qty,
          uom: item.stock_uom || "双",
          stock_uom: item.stock_uom || "双",
          conversion_factor: 1,
        }],
      });
      await API.submitDoc("Stock Entry", doc.name);
      scanLog.unshift({
        time: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
        code: item.item_code, qty, from, to, name: doc.name,
      });
      $("#scan-count").textContent = String(scanLog.length);
      $("#scan-log").innerHTML = scanLog.map(l => `
        <div class="log-item">
          <span class="log-time">${l.time}</span>
          <b>${esc(l.code)}</b>
          <span class="num">×${fmtNum(l.qty)}</span>
          <span style="color:var(--sub);flex:1">${esc(l.from.split(" - ")[0])} → ${esc(l.to.split(" - ")[0])}</span>
          <span class="pill ok mono">${esc(l.name)}</span>
        </div>`).join("");
      toast(`出入库成功：${doc.name}（已提交）`);
      renderScanForm(item, code);
      $("#scan-input").value = "";
      $("#scan-input").focus();
    } catch (e) {
      toast("提交失败：" + e.message, true);
      btn.disabled = false; btn.textContent = "提交出入库";
    }
  });
  $("#scan-qty").focus();
  $("#scan-qty").select();
}

/* ---------------- 应付对账 ---------------- */
PAGES.finance = async function (box) {
  const [pis, pes, gls] = await Promise.all([
    API.list("Purchase Invoice", ["name", "supplier", "posting_date", "grand_total", "status", "docstatus"], [["docstatus", "=", 1]], 200),
    API.list("Payment Entry", ["name", "party", "posting_date", "paid_amount", "status", "docstatus"], [["docstatus", "=", 1], ["party_type", "=", "Supplier"]], 200),
    API.list("GL Entry", ["party", "debit", "credit", "account", "is_cancelled"], [["party_type", "=", "Supplier"], ["is_cancelled", "=", 0], ["account", "=", "债权人 - 奥登科"]], 500),
  ]);
  const suppliers = [...new Set([...pis.map(p => p.supplier), ...pes.map(p => p.party)])];
  const rows = suppliers.map(s => {
    const inv = pis.filter(p => p.supplier === s);
    const pay = pes.filter(p => p.party === s);
    const invAmt = inv.reduce((a, b) => a + (b.grand_total || 0), 0);
    const payAmt = pay.reduce((a, b) => a + (b.paid_amount || 0), 0);
    const bal = gls.filter(g => g.party === s).reduce((a, g) => a + g.debit - g.credit, 0);
    return { s, inv, pay, invAmt, payAmt, bal };
  });
  const totalInv = rows.reduce((a, r) => a + r.invAmt, 0);
  const totalPay = rows.reduce((a, r) => a + r.payAmt, 0);
  box.innerHTML = `
    ${pageHeader("i-fin", "应付对账", "供应商开票、付款与往来余额一表看清",
      `<button class="btn-amber" onclick="openNewDoc('pay')">＋ 登记付款</button><span class="pill ${Math.abs(rows.reduce((a, r) => a + r.bal, 0)) < 0.01 ? "ok" : "wait"}">${rows.length} 家供应商</span>`)}
    <div class="grid g3" style="margin-bottom:14px">
      <div class="card stat-card">
        <span class="stat-ic blue"><svg><use href="#i-order"/></svg></span>
        <div class="stat-body"><div class="stat-label">累计开票</div><div class="stat-value">${fmtNum(totalInv / 10000, 1)}<small>万元</small></div></div>
      </div>
      <div class="card stat-card">
        <span class="stat-ic cyan"><svg><use href="#i-fin"/></svg></span>
        <div class="stat-body"><div class="stat-label">累计付款</div><div class="stat-value">${fmtNum(totalPay / 10000, 1)}<small>万元</small></div></div>
      </div>
      <div class="card stat-card">
        <span class="stat-ic ${Math.abs(rows.reduce((a, r) => a + r.bal, 0)) < 0.01 ? "green" : "amber"}"><svg><use href="#i-chip"/></svg></span>
        <div class="stat-body"><div class="stat-label">未结清余额</div><div class="stat-value">${fmtNum(rows.reduce((a, r) => a + r.bal, 0) / 10000, 2)}<small>万元</small></div></div>
      </div>
    </div>
    <div class="card" style="margin-bottom:14px">
      <div class="card-hd"><h3>厂商对账单</h3></div>
      <table class="tbl"><thead><tr><th>供应商</th><th>发票数</th><th>开票金额</th><th>付款笔数</th><th>已付金额</th><th>应付余额</th></tr></thead>
      <tbody>
        ${rows.map(r => `<tr>
          <td><b>${esc(r.s)}</b></td><td class="num">${r.inv.length}</td><td class="num">${fmtMoney(r.invAmt)}</td>
          <td class="num">${r.pay.length}</td><td class="num">${fmtMoney(r.payAmt)}</td>
          <td class="num ${Math.abs(r.bal) < 0.01 ? "bal-zero" : "bal-open"}">${fmtMoney(r.bal)}</td></tr>`).join("")}
        <tr class="recon-total"><td>合计</td><td class="num">${pis.length}</td><td class="num">${fmtMoney(totalInv)}</td>
          <td class="num">${pes.length}</td><td class="num">${fmtMoney(totalPay)}</td>
          <td class="num ${Math.abs(rows.reduce((a, r) => a + r.bal, 0)) < 0.01 ? "bal-zero" : "bal-open"}">${fmtMoney(rows.reduce((a, r) => a + r.bal, 0))}</td></tr>
      </tbody></table>
    </div>
    <div class="grid g2">
      <div class="card"><div class="card-hd"><h3>应付发票</h3></div>
        <table class="tbl"><thead><tr><th>发票号</th><th>供应商</th><th>金额</th><th>状态</th></tr></thead>
        <tbody>${pis.map(p => `<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.supplier)}</td>
          <td class="num">${fmtMoney(p.grand_total)}</td><td>${statusPill(p.status, p.docstatus)}</td></tr>`).join("")}
        </tbody></table></div>
      <div class="card"><div class="card-hd"><h3>付款单</h3></div>
        <table class="tbl"><thead><tr><th>付款单号</th><th>供应商</th><th>金额</th><th>日期</th></tr></thead>
        <tbody>${pes.map(p => `<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.party)}</td>
          <td class="num">${fmtMoney(p.paid_amount)}</td><td class="num">${fmtDate(p.posting_date)}</td></tr>`).join("")}
        </tbody></table></div>
    </div>`;
};

/* ---------------- SVG 流程图引擎 ---------------- */
const FLOW_COLORS = {
  cyan:   ["rgba(79,209,197,.12)", "#4FD1C5"],
  blue:   ["rgba(127,168,232,.12)", "#7FA8E8"],
  purple: ["rgba(167,139,250,.12)", "#A78BFA"],
  orange: ["rgba(255,176,32,.12)", "#FFB020"],
  green:  ["rgba(110,213,146,.12)", "#6ED592"],
  peach:  ["rgba(255,138,112,.10)", "#FF8A70"],
  yellow: ["rgba(255,196,85,.13)", "#FFC455"],
  gray:   ["rgba(255,255,255,.035)", "#8B96A8"],
  white:  ["rgba(255,255,255,.05)", "#E8EDF6"],
};

/* 渲染 SVG 流程图：nodes[{id,x,y,w,h,t,c,small}] edges[{f,t,key,dash,label}] groups[{x,y,t}] */
function flowRender(cfg) {
  const byId = {};
  for (const n of cfg.nodes) byId[n.id] = { ...n, cx: n.x + n.w / 2, cy: n.y + n.h / 2 };
  const clip = (x1, y1, x2, y2, n) => {
    const dx = x2 - x1, dy = y2 - y1;
    const hw = n.w / 2 + 5, hh = n.h / 2 + 5;
    const sx = dx ? hw / Math.abs(dx) : Infinity;
    const sy = dy ? hh / Math.abs(dy) : Infinity;
    const t = Math.min(sx, sy);
    return [x1 + dx * t, y1 + dy * t];
  };
  let edges = "";
  for (const e of cfg.edges) {
    const a = byId[e.f], b = byId[e.t];
    if (!a || !b) continue;
    const [x1, y1] = clip(a.cx, a.cy, b.cx, b.cy, a);
    const [x2, y2] = clip(b.cx, b.cy, a.cx, a.cy, b);
    const c = e.key ? "rgba(255,176,32,.55)" : "rgba(139,150,168,.42)";
    const label = e.label
      ? `<text x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2 - 6}" fill="#8B96A8" font-size="10" text-anchor="middle">${e.label}</text>` : "";
    edges += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${e.key ? 2 : 1.4}"${e.dash ? ' stroke-dasharray="5 4"' : ""} marker-end="url(#farrow)"/>${label}`;
  }
  let nodes = "";
  for (const n of cfg.nodes) {
    const [fill, stroke] = FLOW_COLORS[n.c || "gray"];
    const fs = n.small ? 11.5 : 13;
    const cx = n.x + n.w / 2, cy = n.y + n.h / 2;
    nodes += `<g class="fnode"><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="10" fill="${fill}" stroke="${stroke}" stroke-opacity=".55" stroke-width="1.2"/><text x="${cx}" y="${cy + fs * 0.36}" fill="#E8EDF6" font-size="${fs}" font-weight="600" text-anchor="middle">${n.t}</text></g>`;
  }
  const groups = (cfg.groups || []).map(g =>
    `<text x="${g.x}" y="${g.y}" fill="#5A6577" font-size="12" font-weight="700" letter-spacing="3">${g.t}</text>`).join("");
  return `<div class="flow-svg-wrap"><svg viewBox="0 0 ${cfg.w} ${cfg.h}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet"><defs><marker id="farrow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="rgba(139,150,168,.75)"/></marker></defs>${groups}${edges}${nodes}</svg></div>`;
}

/* 图一：ERP 总体业务流程（型体→BOM→订单→生产/采购→仓储→财务） */
const FLOW_MAIN = {
  w: 1440, h: 920,
  nodes: [
    { id: "style",  x: 40,   y: 140, w: 130, h: 44, t: "型体产品库", c: "blue" },
    { id: "sample", x: 40,   y: 240, w: 130, h: 44, t: "样品单 3.0", c: "blue" },
    { id: "bom",    x: 40,   y: 340, w: 130, h: 44, t: "量产 BOM", c: "blue" },
    { id: "order",  x: 260,  y: 60,  w: 130, h: 44, t: "订单资料", c: "purple" },
    { id: "calc",   x: 260,  y: 170, w: 130, h: 44, t: "订单用量计算", c: "purple" },
    { id: "plan",     x: 470, y: 60,  w: 130, h: 44, t: "生产计划", c: "orange" },
    { id: "sop",      x: 660, y: 16,  w: 120, h: 40, t: "工艺 SOP", c: "orange", small: 1 },
    { id: "dispatch", x: 660, y: 120, w: 130, h: 44, t: "车间派工单", c: "orange" },
    { id: "workstat", x: 830, y: 180, w: 130, h: 44, t: "部件工位派工", c: "orange" },
    { id: "rework",   x: 1010, y: 240, w: 110, h: 40, t: "生产补单", c: "orange", small: 1 },
    { id: "mrp",   x: 260, y: 300, w: 130, h: 44, t: "采购需求计划", c: "green" },
    { id: "quote", x: 260, y: 390, w: 130, h: 44, t: "物料报价", c: "green" },
    { id: "apply", x: 260, y: 480, w: 130, h: 44, t: "申购管理", c: "green" },
    { id: "po",    x: 470, y: 390, w: 150, h: 44, t: "采购单 / 加工单", c: "green" },
    { id: "temp",    x: 680, y: 390, w: 110, h: 44, t: "暂收单", c: "peach" },
    { id: "qc",      x: 830, y: 390, w: 110, h: 44, t: "检验单", c: "peach" },
    { id: "grn",     x: 980, y: 390, w: 110, h: 44, t: "入库单", c: "peach" },
    { id: "pickreq", x: 680, y: 500, w: 110, h: 44, t: "领料申请", c: "peach" },
    { id: "pick",    x: 830, y: 500, w: 110, h: 44, t: "领料出库", c: "peach" },
    { id: "ap",      x: 1150, y: 390, w: 120, h: 44, t: "应付账款", c: "yellow" },
    { id: "cost",    x: 980, y: 500, w: 110, h: 44, t: "订单成本", c: "yellow" },
    { id: "fee",     x: 470, y: 640, w: 140, h: 44, t: "费用报销管理", c: "yellow" },
    { id: "costhub", x: 660, y: 640, w: 120, h: 44, t: "成本归集", c: "yellow" },
    { id: "voucher", x: 660, y: 730, w: 120, h: 44, t: "凭证管理", c: "yellow" },
    { id: "bs", x: 470, y: 830, w: 120, h: 40, t: "资产负债表", c: "yellow", small: 1 },
    { id: "pl", x: 640, y: 830, w: 100, h: 40, t: "利润表", c: "yellow", small: 1 },
    { id: "cf", x: 790, y: 830, w: 120, h: 40, t: "现金流量表", c: "yellow", small: 1 },
    { id: "oa",    x: 40,  y: 760, w: 130, h: 38, t: "OA 在线签核", c: "cyan", small: 1 },
    { id: "esg",   x: 190, y: 760, w: 130, h: 38, t: "ESG 耗能管理", c: "cyan", small: 1 },
    { id: "mes",   x: 40,  y: 822, w: 130, h: 38, t: "MES 看板管理", c: "cyan", small: 1 },
    { id: "alert", x: 190, y: 822, w: 130, h: 38, t: "预警通知管理", c: "cyan", small: 1 },
  ],
  groups: [
    { x: 40, y: 118, t: "产品数据基础" },
    { x: 40, y: 736, t: "辅助支撑层" },
  ],
  edges: [
    { f: "style", t: "sample", key: 1 }, { f: "sample", t: "bom", key: 1 },
    { f: "bom", t: "calc" },
    { f: "order", t: "plan", key: 1 }, { f: "calc", t: "plan" },
    { f: "calc", t: "mrp", key: 1 },
    { f: "plan", t: "dispatch", key: 1 },
    { f: "sop", t: "workstat" },
    { f: "dispatch", t: "workstat", key: 1 },
    { f: "workstat", t: "rework", dash: 1, label: "" }, { f: "rework", t: "dispatch", dash: 1, label: "补单回流" },
    { f: "mrp", t: "po", key: 1 }, { f: "quote", t: "po" }, { f: "apply", t: "po" },
    { f: "po", t: "temp", key: 1 },
    { f: "temp", t: "qc", key: 1 }, { f: "qc", t: "grn", key: 1 },
    { f: "grn", t: "ap", key: 1 },
    { f: "dispatch", t: "pickreq", key: 1 },
    { f: "pickreq", t: "pick", key: 1 },
    { f: "pick", t: "cost" },
    { f: "fee", t: "costhub" }, { f: "ap", t: "costhub" }, { f: "cost", t: "costhub" },
    { f: "costhub", t: "voucher", key: 1 },
    { f: "voucher", t: "bs", key: 1 }, { f: "voucher", t: "pl", key: 1 }, { f: "voucher", t: "cf", key: 1 },
  ],
};

/* 图二：基础资料与物料编码流程 */
const FLOW_MASTER = {
  w: 1440, h: 880,
  nodes: [
    { id: "g1n1", x: 40,  y: 90,  w: 130, h: 40, t: "公用基础资料", c: "cyan", small: 1 },
    { id: "g1n2", x: 40,  y: 150, w: 130, h: 40, t: "厂别资料", c: "cyan", small: 1 },
    { id: "g1n3", x: 40,  y: 210, w: 130, h: 40, t: "部门资料", c: "cyan", small: 1 },
    { id: "g1n4", x: 40,  y: 270, w: 130, h: 40, t: "车间资料", c: "gray", small: 1 },
    { id: "g2n1", x: 210, y: 90,  w: 130, h: 40, t: "客户资料", c: "yellow", small: 1 },
    { id: "g2n2", x: 210, y: 150, w: 130, h: 40, t: "供应商资料", c: "yellow", small: 1 },
    { id: "g2n3", x: 210, y: 210, w: 150, h: 40, t: "供应商资料(成品)", c: "yellow", small: 1 },
    { id: "g2n4", x: 210, y: 270, w: 130, h: 40, t: "尺码资料", c: "yellow", small: 1 },
    { id: "g2n5", x: 210, y: 330, w: 130, h: 40, t: "部位资料", c: "yellow", small: 1 },
    { id: "g3n1", x: 410, y: 90,  w: 130, h: 40, t: "发票资料", c: "gray", small: 1 },
    { id: "g3n2", x: 410, y: 150, w: 130, h: 40, t: "付款条件", c: "gray", small: 1 },
    { id: "g3n3", x: 410, y: 210, w: 130, h: 40, t: "货币资料", c: "gray", small: 1 },
    { id: "g3n4", x: 410, y: 270, w: 130, h: 40, t: "汇率资料", c: "gray", small: 1 },
    { id: "g3n5", x: 410, y: 330, w: 130, h: 40, t: "单据规则", c: "gray", small: 1 },
    { id: "g3n6", x: 410, y: 390, w: 130, h: 40, t: "采购单位", c: "gray", small: 1 },
    { id: "g4n1", x: 590, y: 90,  w: 150, h: 40, t: "集团分组权限", c: "gray", small: 1 },
    { id: "g4n2", x: 590, y: 150, w: 150, h: 40, t: "数据权限", c: "gray", small: 1 },
    { id: "g4n3", x: 590, y: 210, w: 150, h: 40, t: "代理人", c: "gray", small: 1 },
    { id: "g4n4", x: 590, y: 270, w: 150, h: 40, t: "产品部位结构", c: "gray", small: 1 },
    { id: "g4n5", x: 590, y: 330, w: 150, h: 40, t: "发EMAIL通知人", c: "gray", small: 1 },
    { id: "k1", x: 560,  y: 490, w: 130, h: 46, t: "物料大类", c: "cyan" },
    { id: "k2", x: 560,  y: 580, w: 130, h: 46, t: "加工方法", c: "cyan" },
    { id: "k3", x: 770,  y: 445, w: 130, h: 46, t: "物料品名", c: "blue" },
    { id: "k4", x: 770,  y: 545, w: 130, h: 46, t: "物料规格", c: "blue" },
    { id: "k5", x: 770,  y: 645, w: 130, h: 46, t: "物料颜色", c: "blue" },
    { id: "k6", x: 990,  y: 545, w: 140, h: 50, t: "物料编码", c: "white" },
    { id: "k7", x: 1190, y: 548, w: 150, h: 46, t: "采购管理 3.0", c: "green" },
    { id: "lang1", x: 560, y: 760, w: 150, h: 40, t: "界面多语言维护", c: "purple", small: 1 },
    { id: "lang2", x: 770, y: 760, w: 150, h: 40, t: "基础资料多语言", c: "purple", small: 1 },
  ],
  groups: [
    { x: 40,  y: 66, t: "基础组织资料" },
    { x: 210, y: 66, t: "业务伙伴与产品属性" },
    { x: 410, y: 66, t: "财务与单据规则" },
    { x: 590, y: 66, t: "权限与通知" },
    { x: 560, y: 460, t: "物料编码生成" },
    { x: 560, y: 736, t: "多语言扩展" },
  ],
  edges: [
    { f: "k1", t: "k3", key: 1 },
    { f: "k2", t: "k4", key: 1 },
    { f: "k3", t: "k6", key: 1 },
    { f: "k4", t: "k6", key: 1 },
    { f: "k5", t: "k6", key: 1 },
    { f: "k6", t: "k7", key: 1 },
    { f: "lang1", t: "lang2" },
  ],
};

/* ============ 补充流程图（十张） ============ */
/* 图三：生产制造 MES（计划→派工→品检报工→入出库，四条产线） */
const FLOW_MES = {
  w: 1440, h: 960,
  nodes: [
    { id: "p1", x: 40,  y: 60, w: 130, h: 42, t: "型体产品库", c: "blue" },
    { id: "p2", x: 210, y: 60, w: 120, h: 42, t: "订单资料", c: "white" },
    { id: "p3", x: 360, y: 60, w: 130, h: 42, t: "生产主计划", c: "orange" },
    { id: "p4", x: 520, y: 60, w: 140, h: 42, t: "部门生产计划", c: "orange" },
    { id: "p5", x: 700, y: 60, w: 120, h: 42, t: "生管派工", c: "orange" },
    { id: "s1", x: 40,  y: 150, w: 110, h: 40, t: "装备 SOP", c: "cyan", small: 1 },
    { id: "s2", x: 210, y: 150, w: 110, h: 40, t: "针车 SOP", c: "cyan", small: 1 },
    { id: "s3", x: 360, y: 150, w: 110, h: 40, t: "成型 SOP", c: "cyan", small: 1 },
    { id: "s4", x: 520, y: 150, w: 130, h: 40, t: "其它工段 SOP", c: "cyan", small: 1 },
    { id: "L1a", x: 180, y: 240, w: 120, h: 42, t: "裁备派工", c: "orange" },
    { id: "L1b", x: 180, y: 330, w: 120, h: 42, t: "裁备检验", c: "peach" },
    { id: "L1c", x: 180, y: 420, w: 120, h: 42, t: "裁备报工", c: "orange" },
    { id: "L1d", x: 180, y: 510, w: 120, h: 42, t: "裁备入库", c: "green" },
    { id: "L2a", x: 340, y: 240, w: 120, h: 42, t: "针车派工", c: "orange" },
    { id: "L2b", x: 340, y: 330, w: 120, h: 42, t: "针车检验", c: "peach" },
    { id: "L2c", x: 340, y: 420, w: 120, h: 42, t: "针车报工", c: "orange" },
    { id: "L2d", x: 340, y: 510, w: 120, h: 42, t: "针车入库", c: "green" },
    { id: "L3a", x: 500, y: 240, w: 130, h: 42, t: "成型派工", c: "orange" },
    { id: "L3b", x: 500, y: 330, w: 130, h: 42, t: "成型检验", c: "peach" },
    { id: "L3c", x: 500, y: 420, w: 130, h: 42, t: "成型报工", c: "orange" },
    { id: "L3d", x: 500, y: 510, w: 140, h: 42, t: "成品扫描入库", c: "green" },
    { id: "L4a", x: 680, y: 240, w: 120, h: 42, t: "其它派工", c: "orange" },
    { id: "L4b", x: 680, y: 330, w: 120, h: 42, t: "其它检验", c: "peach" },
    { id: "L4c", x: 680, y: 420, w: 120, h: 42, t: "其它报工", c: "orange" },
    { id: "L4d", x: 680, y: 510, w: 120, h: 42, t: "其它入库", c: "green" },
    { id: "q1", x: 880, y: 640, w: 130, h: 42, t: "大屏看板", c: "cyan" },
    { id: "q2", x: 880, y: 700, w: 150, h: 42, t: "生产日报 / 月报", c: "cyan" },
    { id: "q3", x: 880, y: 760, w: 150, h: 42, t: "移动 APP 查询", c: "cyan" },
    { id: "q4", x: 1080, y: 700, w: 150, h: 42, t: "条码查询中心", c: "cyan" },
    { id: "note", x: 880, y: 240, w: 160, h: 42, t: "PDA / 平板作业", c: "purple", small: 1 },
    { id: "note2", x: 1080, y: 240, w: 170, h: 42, t: "线上工艺标签打印", c: "purple", small: 1 },
  ],
  groups: [
    { x: 40, y: 34, t: "计划与派工" },
    { x: 40, y: 124, t: "工段SOP" },
    { x: 180, y: 214, t: "裁备线" },
    { x: 340, y: 214, t: "针车线" },
    { x: 500, y: 214, t: "成型线" },
    { x: 680, y: 214, t: "其它工段" },
    { x: 880, y: 614, t: "综合查询" },
  ],
  edges: [
    { f: "p1", t: "p2", key: 1 }, { f: "p2", t: "p3", key: 1 }, { f: "p3", t: "p4", key: 1 }, { f: "p4", t: "p5", key: 1 },
    { f: "p5", t: "L1a" }, { f: "p5", t: "L2a" }, { f: "p5", t: "L3a", key: 1 }, { f: "p5", t: "L4a" },
    { f: "L1a", t: "L1b", key: 1 }, { f: "L1b", t: "L1c", key: 1 }, { f: "L1c", t: "L1d", key: 1 },
    { f: "L2a", t: "L2b", key: 1 }, { f: "L2b", t: "L2c", key: 1 }, { f: "L2c", t: "L2d", key: 1 },
    { f: "L3a", t: "L3b", key: 1 }, { f: "L3b", t: "L3c", key: 1 }, { f: "L3c", t: "L3d", key: 1 },
    { f: "L4a", t: "L4b", key: 1 }, { f: "L4b", t: "L4c", key: 1 }, { f: "L4c", t: "L4d", key: 1 },
    { f: "L3d", t: "q1" },
  ],
};

/* 图四：品质检验管理 */
const FLOW_QC = {
  w: 1440, h: 800,
  nodes: [
    { id: "i1", x: 40,  y: 60,  w: 120, h: 42, t: "订单资料", c: "white" },
    { id: "i2", x: 200, y: 60,  w: 120, h: 42, t: "生产派工", c: "white" },
    { id: "i3", x: 40,  y: 160, w: 130, h: 42, t: "品检基础资料", c: "cyan" },
    { id: "i4", x: 40,  y: 240, w: 130, h: 42, t: "工段检验项目", c: "cyan" },
    { id: "i5", x: 40,  y: 560, w: 120, h: 42, t: "测试项目", c: "cyan" },
    { id: "c1", x: 360, y: 100, w: 130, h: 42, t: "裁断车间检验", c: "orange" },
    { id: "c2", x: 360, y: 190, w: 130, h: 42, t: "针车车间检验", c: "orange" },
    { id: "c3", x: 360, y: 280, w: 130, h: 42, t: "成型车间检验", c: "orange" },
    { id: "c4", x: 360, y: 370, w: 130, h: 42, t: "手工车间检验", c: "orange" },
    { id: "c5", x: 360, y: 460, w: 130, h: 42, t: "成品验货报告", c: "orange" },
    { id: "c6", x: 360, y: 550, w: 120, h: 42, t: "翻箱报告", c: "orange" },
    { id: "c7", x: 200, y: 640, w: 120, h: 42, t: "送测登记", c: "orange" },
    { id: "c8", x: 360, y: 640, w: 120, h: 42, t: "测试结果", c: "orange" },
    { id: "on", x: 600, y: 190, w: 130, h: 42, t: "针车线上检验", c: "purple" },
    { id: "r1", x: 820, y: 100, w: 140, h: 42, t: "检验不良率表", c: "yellow", small: 1 },
    { id: "r2", x: 820, y: 190, w: 150, h: 42, t: "生产检验日报表", c: "yellow", small: 1 },
    { id: "r3", x: 820, y: 280, w: 130, h: 42, t: "RFT 月统计表", c: "yellow", small: 1 },
    { id: "r4", x: 820, y: 370, w: 130, h: 42, t: "品质日报表", c: "yellow", small: 1 },
    { id: "r5", x: 820, y: 460, w: 150, h: 42, t: "品质状况月报表", c: "yellow", small: 1 },
  ],
  groups: [
    { x: 360, y: 74, t: "检验执行" },
    { x: 820, y: 74, t: "品质报表" },
  ],
  edges: [
    { f: "i1", t: "i2", key: 1 }, { f: "i2", t: "c1" },
    { f: "i3", t: "c1" }, { f: "i4", t: "c2" },
    { f: "c1", t: "c2", key: 1 }, { f: "c2", t: "c3", key: 1 }, { f: "c3", t: "c4", key: 1 },
    { f: "c4", t: "c5", key: 1 }, { f: "c5", t: "c6", key: 1 },
    { f: "i5", t: "c7" }, { f: "c7", t: "c8", key: 1 },
    { f: "c2", t: "on", dash: 1 },
    { f: "c1", t: "r1" }, { f: "c2", t: "r2" }, { f: "c3", t: "r3" }, { f: "c4", t: "r4" }, { f: "c5", t: "r5" },
  ],
};

/* 图五：半成品库存管理 */
const FLOW_SFC = {
  w: 1440, h: 820,
  nodes: [
    { id: "i1", x: 40,  y: 80,  w: 120, h: 42, t: "仓库资料", c: "cyan" },
    { id: "i2", x: 40,  y: 180, w: 120, h: 42, t: "订单资料", c: "white" },
    { id: "i3", x: 200, y: 180, w: 120, h: 42, t: "针车派工", c: "white" },
    { id: "i4", x: 40,  y: 280, w: 130, h: 42, t: "生产产量录入", c: "orange" },
    { id: "i5", x: 40,  y: 380, w: 130, h: 42, t: "出入库类别", c: "cyan" },
    { id: "i6", x: 40,  y: 480, w: 130, h: 42, t: "半库存初始化", c: "cyan" },
    { id: "a1", x: 400, y: 180, w: 130, h: 44, t: "半成品入库", c: "orange" },
    { id: "hub", x: 600, y: 380, w: 140, h: 48, t: "半成品库存", c: "green" },
    { id: "a2", x: 820, y: 380, w: 130, h: 44, t: "半成品出库", c: "orange" },
    { id: "u1", x: 820, y: 80,  w: 120, h: 42, t: "生产补单", c: "orange" },
    { id: "u2", x: 820, y: 160, w: 130, h: 42, t: "申购管理 3.0", c: "orange" },
    { id: "u3", x: 820, y: 240, w: 150, h: 42, t: "非生产领料申请", c: "orange", small: 1 },
    { id: "v1", x: 820, y: 480, w: 140, h: 42, t: "半成品库存盘点", c: "orange", small: 1 },
    { id: "v2", x: 1010, y: 480, w: 140, h: 42, t: "半成品库存调整", c: "orange", small: 1 },
    { id: "v3", x: 1010, y: 560, w: 140, h: 42, t: "半成品库存结转", c: "orange", small: 1 },
    { id: "r1", x: 1220, y: 80,  w: 140, h: 42, t: "订单用量 3.0", c: "yellow", small: 1 },
    { id: "r2", x: 1220, y: 160, w: 150, h: 42, t: "半成品进销存报表", c: "yellow", small: 1 },
    { id: "r3", x: 1220, y: 240, w: 150, h: 42, t: "半成品日进出明细", c: "yellow", small: 1 },
    { id: "r4", x: 1220, y: 320, w: 150, h: 42, t: "半成品进出统计表", c: "yellow", small: 1 },
    { id: "r5", x: 1220, y: 400, w: 140, h: 42, t: "半成品配套表", c: "yellow", small: 1 },
  ],
  groups: [
    { x: 40, y: 54, t: "基础与输入" },
    { x: 1220, y: 54, t: "库存报表" },
  ],
  edges: [
    { f: "i2", t: "i3", key: 1 }, { f: "i3", t: "a1", key: 1 },
    { f: "i4", t: "a1" }, { f: "i1", t: "a1" }, { f: "i5", t: "a1" },
    { f: "a1", t: "hub", key: 1 }, { f: "i6", t: "hub" },
    { f: "hub", t: "a2", key: 1 },
    { f: "u1", t: "hub", dash: 1 }, { f: "u2", t: "hub", dash: 1 }, { f: "u3", t: "a2" },
    { f: "hub", t: "v1", key: 1 }, { f: "v1", t: "v2", key: 1 }, { f: "hub", t: "v3", dash: 1 },
    { f: "hub", t: "r1" }, { f: "hub", t: "r2" }, { f: "hub", t: "r3" },
  ],
};

/* 图六：成品库存与条码（双轨） */
const FLOW_FG = {
  w: 1440, h: 900,
  nodes: [
    { id: "l1", x: 40,  y: 60,  w: 120, h: 42, t: "仓库资料", c: "cyan" },
    { id: "l2", x: 40,  y: 150, w: 120, h: 42, t: "订单资料", c: "white" },
    { id: "l3", x: 200, y: 150, w: 130, h: 42, t: "生产派工单", c: "white" },
    { id: "l4", x: 400, y: 150, w: 120, h: 42, t: "成品入库", c: "orange" },
    { id: "l5", x: 40,  y: 430, w: 120, h: 42, t: "出货通知", c: "white" },
    { id: "l6", x: 400, y: 430, w: 120, h: 42, t: "成品出库", c: "orange" },
    { id: "l7", x: 600, y: 430, w: 140, h: 42, t: "出货应收明细", c: "yellow", small: 1 },
    { id: "hub", x: 260, y: 290, w: 150, h: 50, t: "成品库存信息", c: "green" },
    { id: "o1", x: 620, y: 560, w: 130, h: 42, t: "成品库存盘点", c: "orange", small: 1 },
    { id: "o2", x: 620, y: 640, w: 130, h: 42, t: "成品库存调整", c: "orange", small: 1 },
    { id: "o3", x: 620, y: 720, w: 130, h: 42, t: "成品库存结转", c: "orange", small: 1 },
    { id: "b1", x: 840, y: 60,  w: 120, h: 42, t: "订单装箱", c: "orange" },
    { id: "b2", x: 840, y: 150, w: 140, h: 42, t: "订单条码管理", c: "orange", small: 1 },
    { id: "b3", x: 840, y: 240, w: 130, h: 42, t: "成型装盒扫描", c: "purple", small: 1 },
    { id: "b4", x: 840, y: 330, w: 150, h: 42, t: "订单装箱扫描检测", c: "purple", small: 1 },
    { id: "b5", x: 840, y: 430, w: 140, h: 42, t: "成品扫描入库", c: "orange", small: 1 },
    { id: "b6", x: 840, y: 560, w: 140, h: 42, t: "成品扫描出库", c: "orange", small: 1 },
    { id: "b7", x: 840, y: 700, w: 140, h: 42, t: "条码查询中心", c: "cyan", small: 1 },
    { id: "r1", x: 1120, y: 60,  w: 150, h: 42, t: "成品进销存报表", c: "yellow", small: 1 },
    { id: "r2", x: 1120, y: 140, w: 150, h: 42, t: "成品日进出明细表", c: "yellow", small: 1 },
    { id: "r3", x: 1120, y: 220, w: 150, h: 42, t: "成品进出统计表", c: "yellow", small: 1 },
    { id: "r4", x: 1120, y: 300, w: 150, h: 42, t: "成品入库欠数明细", c: "yellow", small: 1 },
  ],
  groups: [
    { x: 40, y: 34, t: "传统账务流" },
    { x: 840, y: 34, t: "条码实物流" },
    { x: 1120, y: 34, t: "成品报表" },
  ],
  edges: [
    { f: "l2", t: "l3", key: 1 }, { f: "l3", t: "l4", key: 1 },
    { f: "l1", t: "hub" }, { f: "l4", t: "hub", key: 1 },
    { f: "hub", t: "l6", key: 1 }, { f: "l5", t: "l6" }, { f: "l6", t: "l7", key: 1 },
    { f: "hub", t: "o1" }, { f: "hub", t: "o2" }, { f: "hub", t: "o3" },
    { f: "b1", t: "b2", key: 1 }, { f: "b2", t: "b4", key: 1 }, { f: "b3", t: "b2", dash: 1 },
    { f: "b4", t: "b5", key: 1 }, { f: "b5", t: "hub", key: 1 },
    { f: "b5", t: "b6", dash: 1 }, { f: "l5", t: "b6" }, { f: "b6", t: "b7" },
    { f: "hub", t: "r1" }, { f: "hub", t: "r2" }, { f: "hub", t: "r3" }, { f: "hub", t: "r4" },
  ],
};

/* 图七：应收账款 */
const FLOW_AR = {
  w: 1440, h: 800,
  nodes: [
    { id: "s1", x: 40,  y: 60,  w: 120, h: 42, t: "成品出货", c: "white" },
    { id: "s2", x: 40,  y: 140, w: 120, h: 42, t: "样品出货", c: "white" },
    { id: "s3", x: 40,  y: 220, w: 120, h: 42, t: "外卖材料", c: "white" },
    { id: "s4", x: 40,  y: 300, w: 140, h: 42, t: "成品退货入库", c: "white", small: 1 },
    { id: "s5", x: 40,  y: 380, w: 140, h: 42, t: "SKU 单价管理", c: "cyan", small: 1 },
    { id: "e0", x: 240, y: 60,  w: 120, h: 42, t: "应收项目", c: "cyan" },
    { id: "e1", x: 240, y: 150, w: 140, h: 42, t: "订单预收申请", c: "orange", small: 1 },
    { id: "e2", x: 440, y: 190, w: 140, h: 44, t: "出货应收明细", c: "orange" },
    { id: "e3", x: 660, y: 190, w: 130, h: 44, t: "应收对账单", c: "orange" },
    { id: "e4", x: 860, y: 190, w: 120, h: 44, t: "收款单", c: "orange" },
    { id: "e5", x: 1060, y: 190, w: 120, h: 44, t: "收支管理", c: "green" },
    { id: "e6", x: 440, y: 320, w: 120, h: 42, t: "其他应收", c: "orange" },
    { id: "e7", x: 660, y: 320, w: 130, h: 42, t: "应收扣款单", c: "orange" },
    { id: "e8", x: 860, y: 320, w: 130, h: 42, t: "客户发票管理", c: "cyan", small: 1 },
    { id: "e9", x: 860, y: 400, w: 120, h: 42, t: "应收初始化", c: "blue", small: 1 },
    { id: "r1", x: 1240, y: 60,  w: 130, h: 42, t: "收款明细表", c: "yellow", small: 1 },
    { id: "r2", x: 1240, y: 140, w: 130, h: 42, t: "未收统计表", c: "yellow", small: 1 },
    { id: "r3", x: 1240, y: 220, w: 130, h: 42, t: "收款汇总表", c: "yellow", small: 1 },
    { id: "r4", x: 1240, y: 300, w: 130, h: 42, t: "应收对账表", c: "yellow", small: 1 },
    { id: "r5", x: 1240, y: 380, w: 130, h: 42, t: "扣款明细表", c: "yellow", small: 1 },
    { id: "r6", x: 1240, y: 460, w: 140, h: 42, t: "其他应收明细表", c: "yellow", small: 1 },
  ],
  groups: [
    { x: 40, y: 34, t: "业务来源" },
    { x: 240, y: 34, t: "应收流程" },
    { x: 1240, y: 34, t: "应收报表" },
  ],
  edges: [
    { f: "s1", t: "e2", key: 1 }, { f: "s2", t: "e2" }, { f: "s3", t: "e2" }, { f: "s4", t: "e2", dash: 1 }, { f: "s5", t: "e2" },
    { f: "e0", t: "e1", key: 1 }, { f: "e0", t: "e6" },
    { f: "e2", t: "e3", key: 1 }, { f: "e6", t: "e3" }, { f: "e7", t: "e3" },
    { f: "e3", t: "e4", key: 1 }, { f: "e8", t: "e4" }, { f: "e9", t: "e4" },
    { f: "e4", t: "e5", key: 1 },
    { f: "e4", t: "r1" }, { f: "e3", t: "r4" }, { f: "e7", t: "r5" }, { f: "e6", t: "r6" },
  ],
};

/* 图八：应付账款 */
const FLOW_AP = {
  w: 1440, h: 820,
  nodes: [
    { id: "s1", x: 40,  y: 80,  w: 120, h: 42, t: "委外入库", c: "white" },
    { id: "s2", x: 40,  y: 160, w: 120, h: 42, t: "验收入库", c: "white" },
    { id: "s3", x: 40,  y: 240, w: 120, h: 42, t: "采购退货", c: "white" },
    { id: "s4", x: 40,  y: 320, w: 120, h: 42, t: "材料报价", c: "cyan" },
    { id: "e0", x: 240, y: 80,  w: 120, h: 42, t: "应付项目", c: "cyan" },
    { id: "e1", x: 240, y: 180, w: 140, h: 44, t: "验收应付明细", c: "orange" },
    { id: "e2", x: 460, y: 180, w: 140, h: 44, t: "工厂应付确认", c: "orange" },
    { id: "e3", x: 680, y: 180, w: 130, h: 44, t: "应付对账单", c: "orange" },
    { id: "e4", x: 880, y: 180, w: 120, h: 44, t: "付款单", c: "orange" },
    { id: "e5", x: 1080, y: 180, w: 120, h: 44, t: "收支管理", c: "green" },
    { id: "e6", x: 460, y: 320, w: 120, h: 42, t: "其他应付", c: "orange" },
    { id: "e7", x: 680, y: 320, w: 130, h: 42, t: "应付扣款单", c: "orange" },
    { id: "e8", x: 880, y: 320, w: 120, h: 42, t: "应付初始化", c: "blue", small: 1 },
    { id: "e9", x: 880, y: 400, w: 120, h: 42, t: "发票登记", c: "cyan", small: 1 },
    { id: "r1", x: 1260, y: 60,  w: 130, h: 42, t: "应付账龄分析", c: "yellow", small: 1 },
    { id: "r2", x: 1260, y: 140, w: 130, h: 42, t: "应付明细表", c: "yellow", small: 1 },
    { id: "r3", x: 1260, y: 220, w: 140, h: 42, t: "对账明细表", c: "yellow", small: 1 },
    { id: "r4", x: 1260, y: 300, w: 130, h: 42, t: "未付统计表", c: "yellow", small: 1 },
    { id: "r5", x: 1260, y: 380, w: 130, h: 42, t: "付款汇总表", c: "yellow", small: 1 },
    { id: "r6", x: 1260, y: 460, w: 140, h: 42, t: "采购差异分析", c: "yellow", small: 1 },
  ],
  groups: [
    { x: 40, y: 54, t: "业务来源" },
    { x: 240, y: 54, t: "应付流程" },
    { x: 1260, y: 54, t: "应付报表" },
  ],
  edges: [
    { f: "s1", t: "e1", key: 1 }, { f: "s2", t: "e1", key: 1 }, { f: "s3", t: "e1", dash: 1 }, { f: "s4", t: "e1" },
    { f: "e0", t: "e6" },
    { f: "e1", t: "e2", key: 1 }, { f: "e2", t: "e3", key: 1 },
    { f: "e6", t: "e3" }, { f: "e7", t: "e3" },
    { f: "e3", t: "e4", key: 1 }, { f: "e8", t: "e4" }, { f: "e9", t: "e4" },
    { f: "e4", t: "e5", key: 1 },
    { f: "e3", t: "r3" }, { f: "e4", t: "r5" }, { f: "e7", t: "r4", dash: 1 },
  ],
};

/* 图九：成本核算 */
const FLOW_COST = {
  w: 1440, h: 860,
  nodes: [
    { id: "s1", x: 40,  y: 80,  w: 120, h: 42, t: "材料加工", c: "white" },
    { id: "s2", x: 40,  y: 160, w: 120, h: 42, t: "成品入库", c: "white" },
    { id: "s3", x: 40,  y: 240, w: 120, h: 42, t: "仓库发料", c: "white" },
    { id: "s4", x: 40,  y: 320, w: 120, h: 42, t: "委外入库", c: "white" },
    { id: "c1", x: 220, y: 80,  w: 130, h: 42, t: "加工料核销", c: "orange" },
    { id: "c2", x: 400, y: 80,  w: 140, h: 42, t: "物料存货核算", c: "orange", small: 1 },
    { id: "c3", x: 220, y: 240, w: 120, h: 44, t: "成本项目", c: "orange" },
    { id: "c4", x: 420, y: 240, w: 120, h: 44, t: "成本计算", c: "orange" },
    { id: "c5", x: 600, y: 240, w: 120, h: 44, t: "成本结转", c: "orange" },
    { id: "c6", x: 780, y: 240, w: 140, h: 44, t: "成品存货核算", c: "orange", small: 1 },
    { id: "c7", x: 980, y: 240, w: 140, h: 44, t: "销售成本计算", c: "orange", small: 1 },
    { id: "c8", x: 1180, y: 240, w: 140, h: 44, t: "自动生成凭证", c: "green", small: 1 },
    { id: "std1", x: 620, y: 80,  w: 140, h: 42, t: "订单标准成本", c: "orange", small: 1 },
    { id: "std2", x: 820, y: 80,  w: 150, h: 42, t: "订单标准成本表", c: "yellow", small: 1 },
    { id: "p1", x: 220, y: 420, w: 120, h: 42, t: "分摊方式", c: "cyan" },
    { id: "p2", x: 420, y: 420, w: 120, h: 42, t: "成控中心", c: "cyan" },
    { id: "x1", x: 1180, y: 80, w: 160, h: 42, t: "完工订单异常追踪表", c: "purple", small: 1 },
    { id: "r1", x: 100, y: 640, w: 130, h: 42, t: "进销存报表", c: "yellow", small: 1 },
    { id: "r2", x: 280, y: 640, w: 150, h: 42, t: "领料金额汇总表", c: "yellow", small: 1 },
    { id: "r3", x: 480, y: 640, w: 130, h: 42, t: "订单成本汇总", c: "yellow", small: 1 },
    { id: "r4", x: 660, y: 640, w: 160, h: 42, t: "标准成本汇总(CBD)", c: "yellow", small: 1 },
    { id: "r5", x: 880, y: 640, w: 120, h: 42, t: "财务锁账", c: "green", small: 1 },
  ],
  groups: [
    { x: 40, y: 54, t: "业务触发" },
    { x: 100, y: 614, t: "成本报表与锁账" },
  ],
  edges: [
    { f: "s1", t: "c1", key: 1 },
    { f: "c1", t: "c2", key: 1 },
    { f: "c2", t: "std1", key: 1 }, { f: "std1", t: "std2", key: 1 },
    { f: "s2", t: "c3" }, { f: "s3", t: "c3" }, { f: "s4", t: "c3" },
    { f: "c3", t: "c4", key: 1 }, { f: "p1", t: "c4" },
    { f: "c4", t: "c5", key: 1 }, { f: "p2", t: "c5" },
    { f: "c5", t: "c6", key: 1 }, { f: "c6", t: "c7", key: 1 },
    { f: "c7", t: "c8", key: 1 },
    { f: "c8", t: "r5", key: 1 },
  ],
};

/* 图十：固定资产 */
const FLOW_ASSET = {
  w: 1440, h: 760,
  nodes: [
    { id: "i1", x: 40,  y: 80,  w: 120, h: 42, t: "资产类别", c: "cyan" },
    { id: "i2", x: 40,  y: 160, w: 120, h: 42, t: "使用情况", c: "cyan" },
    { id: "i3", x: 40,  y: 240, w: 120, h: 42, t: "增减方式", c: "cyan" },
    { id: "i4", x: 40,  y: 320, w: 120, h: 42, t: "存放地址", c: "cyan" },
    { id: "hub", x: 260, y: 200, w: 130, h: 46, t: "资产明细", c: "orange" },
    { id: "d1", x: 260, y: 80,  w: 120, h: 42, t: "调动类别", c: "cyan" },
    { id: "a1", x: 480, y: 60,  w: 120, h: 42, t: "资产领用", c: "orange" },
    { id: "a2", x: 480, y: 140, w: 120, h: 42, t: "资产调动", c: "orange" },
    { id: "a3", x: 480, y: 220, w: 120, h: 42, t: "资产变动", c: "orange" },
    { id: "a4", x: 480, y: 300, w: 120, h: 42, t: "资产维修", c: "orange" },
    { id: "a5", x: 480, y: 380, w: 120, h: 42, t: "资产减少", c: "orange" },
    { id: "a6", x: 480, y: 460, w: 120, h: 42, t: "资产盘点", c: "orange" },
    { id: "dep", x: 260, y: 460, w: 120, h: 42, t: "资产折旧", c: "orange" },
    { id: "o1", x: 700, y: 140, w: 130, h: 42, t: "调动追踪表", c: "yellow", small: 1 },
    { id: "o2", x: 700, y: 220, w: 130, h: 42, t: "变动追踪表", c: "yellow", small: 1 },
    { id: "o3", x: 700, y: 300, w: 120, h: 42, t: "其他应付", c: "green" },
    { id: "o4", x: 700, y: 380, w: 120, h: 42, t: "收支管理", c: "green" },
    { id: "o5", x: 700, y: 460, w: 120, h: 42, t: "盘点扫描", c: "cyan", small: 1 },
    { id: "o6", x: 700, y: 560, w: 130, h: 42, t: "总账凭证", c: "green" },
  ],
  groups: [
    { x: 40, y: 54, t: "基础属性" },
    { x: 480, y: 34, t: "资产业务操作" },
    { x: 700, y: 34, t: "结果与财务" },
  ],
  edges: [
    { f: "i1", t: "hub", key: 1 }, { f: "i2", t: "hub" }, { f: "i3", t: "hub" }, { f: "i4", t: "hub" },
    { f: "hub", t: "a1", key: 1 }, { f: "hub", t: "a2", key: 1 }, { f: "hub", t: "a3", key: 1 },
    { f: "hub", t: "a4", key: 1 }, { f: "hub", t: "a5", key: 1 }, { f: "hub", t: "a6", key: 1 },
    { f: "d1", t: "a2" },
    { f: "a2", t: "o1" }, { f: "a3", t: "o2" },
    { f: "a4", t: "o3" }, { f: "o3", t: "o4" },
    { f: "a6", t: "o5" },
    { f: "hub", t: "dep", key: 1 }, { f: "dep", t: "o6", key: 1 },
  ],
};

/* 图十一：财务总账 */
const FLOW_GL = {
  w: 1440, h: 900,
  nodes: [
    { id: "b1", x: 40,  y: 60,  w: 120, h: 42, t: "基本资料", c: "cyan" },
    { id: "b2", x: 40,  y: 130, w: 120, h: 42, t: "核算项目", c: "cyan" },
    { id: "b3", x: 40,  y: 200, w: 120, h: 42, t: "科目管理", c: "cyan" },
    { id: "b4", x: 40,  y: 270, w: 120, h: 42, t: "会计期间", c: "cyan" },
    { id: "b5", x: 40,  y: 340, w: 130, h: 42, t: "科目初始化", c: "cyan", small: 1 },
    { id: "b6", x: 40,  y: 470, w: 140, h: 42, t: "期间汇率管理", c: "cyan", small: 1 },
    { id: "b7", x: 40,  y: 540, w: 150, h: 42, t: "转凭证科目设置", c: "cyan", small: 1 },
    { id: "b8", x: 40,  y: 610, w: 120, h: 42, t: "报表公式", c: "cyan", small: 1 },
    { id: "g0", x: 240, y: 340, w: 120, h: 44, t: "收支管理", c: "green" },
    { id: "g1", x: 240, y: 170, w: 120, h: 42, t: "收款单", c: "white" },
    { id: "g2", x: 240, y: 240, w: 120, h: 42, t: "付款单", c: "white" },
    { id: "g3", x: 240, y: 600, w: 130, h: 42, t: "报销申请单", c: "white", small: 1 },
    { id: "g4", x: 420, y: 340, w: 120, h: 44, t: "凭证录入", c: "orange" },
    { id: "g5", x: 420, y: 170, w: 140, h: 42, t: "自动生成凭证", c: "orange", small: 1 },
    { id: "g6", x: 580, y: 340, w: 120, h: 44, t: "凭证审核", c: "orange" },
    { id: "g7", x: 740, y: 340, w: 120, h: 44, t: "凭证过账", c: "orange" },
    { id: "g8", x: 900, y: 340, w: 120, h: 44, t: "期末调汇", c: "orange" },
    { id: "g9", x: 1060, y: 440, w: 120, h: 44, t: "损益结转", c: "orange" },
    { id: "g10", x: 1060, y: 560, w: 120, h: 44, t: "期末结账", c: "green" },
    { id: "k1", x: 740, y: 480, w: 120, h: 42, t: "日记账", c: "yellow", small: 1 },
    { id: "k2", x: 740, y: 550, w: 130, h: 42, t: "明细分类账", c: "yellow", small: 1 },
    { id: "k3", x: 740, y: 620, w: 130, h: 42, t: "总分类账", c: "yellow", small: 1 },
    { id: "k4", x: 740, y: 690, w: 120, h: 42, t: "科目余额", c: "yellow", small: 1 },
    { id: "f1", x: 1060, y: 660, w: 130, h: 42, t: "资产负债表", c: "yellow", small: 1 },
    { id: "f2", x: 1220, y: 560, w: 110, h: 42, t: "利润表", c: "yellow", small: 1 },
    { id: "f3", x: 1220, y: 660, w: 130, h: 42, t: "现金流量表", c: "yellow", small: 1 },
    { id: "f4", x: 1220, y: 740, w: 130, h: 42, t: "现金流量项目", c: "cyan", small: 1 },
  ],
  groups: [
    { x: 40, y: 34, t: "基础设置" },
    { x: 420, y: 54, t: "凭证处理" },
    { x: 1060, y: 34, t: "期末处理" },
    { x: 740, y: 454, t: "账簿" },
  ],
  edges: [
    { f: "g1", t: "g0", key: 1 }, { f: "g2", t: "g0", key: 1 }, { f: "g3", t: "g0" },
    { f: "g0", t: "g4", key: 1 }, { f: "b5", t: "g4" }, { f: "g5", t: "g4" }, { f: "b7", t: "g5" },
    { f: "g4", t: "g6", key: 1 }, { f: "g6", t: "g7", key: 1 },
    { f: "g7", t: "g8", key: 1 }, { f: "b6", t: "g8" },
    { f: "g8", t: "g9", key: 1 }, { f: "g9", t: "g10", key: 1 },
    { f: "g9", t: "f1", key: 1 }, { f: "g9", t: "f2", key: 1 }, { f: "g9", t: "f3", key: 1 },
    { f: "b8", t: "f2" }, { f: "f4", t: "f3" },
    { f: "g7", t: "k1" }, { f: "g7", t: "k2" }, { f: "g7", t: "k3" }, { f: "g7", t: "k4" },
  ],
};

/* 图十二：人力资源 */
const FLOW_HR = {
  w: 1440, h: 900,
  nodes: [
    { id: "h1", x: 40,  y: 80,  w: 120, h: 42, t: "基本资料", c: "cyan" },
    { id: "h2", x: 40,  y: 150, w: 120, h: 42, t: "部门资料", c: "cyan" },
    { id: "h3", x: 40,  y: 220, w: 120, h: 42, t: "职位资料", c: "cyan" },
    { id: "h4", x: 40,  y: 290, w: 120, h: 42, t: "工种资料", c: "cyan" },
    { id: "h5", x: 40,  y: 360, w: 120, h: 42, t: "保险项目", c: "cyan" },
    { id: "h6", x: 40,  y: 430, w: 120, h: 42, t: "奖惩项目", c: "cyan" },
    { id: "emp", x: 240, y: 240, w: 120, h: 46, t: "职工档案", c: "orange" },
    { id: "e1", x: 440, y: 60,  w: 120, h: 42, t: "劳动合同", c: "orange" },
    { id: "e2", x: 440, y: 130, w: 120, h: 42, t: "升迁调动", c: "orange" },
    { id: "e3", x: 440, y: 200, w: 120, h: 42, t: "培训记录", c: "orange" },
    { id: "e4", x: 440, y: 270, w: 120, h: 42, t: "宿舍管理", c: "orange" },
    { id: "e5", x: 440, y: 340, w: 120, h: 42, t: "离职作业", c: "orange" },
    { id: "k1", x: 40,  y: 560, w: 120, h: 42, t: "考勤类别", c: "cyan" },
    { id: "k2", x: 40,  y: 630, w: 120, h: 42, t: "班次设置", c: "cyan" },
    { id: "k3", x: 220, y: 560, w: 120, h: 42, t: "打卡记录", c: "white" },
    { id: "k4", x: 220, y: 630, w: 120, h: 42, t: "补卡记录", c: "white" },
    { id: "k5", x: 220, y: 700, w: 120, h: 42, t: "异常考勤", c: "white" },
    { id: "d1", x: 420, y: 630, w: 120, h: 42, t: "考勤日报", c: "orange" },
    { id: "d2", x: 600, y: 630, w: 120, h: 42, t: "考勤汇总", c: "orange" },
    { id: "d3", x: 420, y: 710, w: 120, h: 42, t: "标准工时", c: "cyan" },
    { id: "p1", x: 800, y: 560, w: 120, h: 42, t: "费用项目", c: "cyan" },
    { id: "p2", x: 800, y: 630, w: 120, h: 42, t: "薪资项目", c: "cyan" },
    { id: "p3", x: 980, y: 560, w: 130, h: 42, t: "行政费用记录", c: "orange", small: 1 },
    { id: "p4", x: 980, y: 630, w: 120, h: 42, t: "调薪明细", c: "orange", small: 1 },
    { id: "pay", x: 1180, y: 620, w: 130, h: 50, t: "薪资计算", c: "green" },
    { id: "r1", x: 800, y: 60,  w: 130, h: 42, t: "人事档案表", c: "yellow", small: 1 },
    { id: "r2", x: 800, y: 130, w: 130, h: 42, t: "离职分析表", c: "yellow", small: 1 },
    { id: "r3", x: 800, y: 200, w: 150, h: 42, t: "出勤人数统计表", c: "yellow", small: 1 },
    { id: "r4", x: 800, y: 270, w: 130, h: 42, t: "薪资分析表", c: "yellow", small: 1 },
  ],
  groups: [
    { x: 40, y: 54, t: "人事基础资料" },
    { x: 40, y: 534, t: "考勤管理" },
    { x: 800, y: 534, t: "薪资核算" },
    { x: 800, y: 34, t: "人事报表" },
  ],
  edges: [
    { f: "h1", t: "emp", key: 1 }, { f: "h2", t: "emp" }, { f: "h3", t: "emp" }, { f: "h4", t: "emp" }, { f: "h5", t: "emp" }, { f: "h6", t: "emp" },
    { f: "emp", t: "e1", key: 1 }, { f: "emp", t: "e2", key: 1 }, { f: "emp", t: "e3", key: 1 }, { f: "emp", t: "e4", key: 1 }, { f: "emp", t: "e5", key: 1 },
    { f: "k3", t: "d1", key: 1 }, { f: "k4", t: "d1" }, { f: "k5", t: "d1" }, { f: "k1", t: "d1" }, { f: "k2", t: "d1" },
    { f: "d1", t: "d2", key: 1 }, { f: "d3", t: "d2" },
    { f: "p1", t: "p3" }, { f: "p2", t: "p4" },
    { f: "d2", t: "pay", key: 1 }, { f: "p3", t: "pay", key: 1 }, { f: "p4", t: "pay", key: 1 },
    { f: "emp", t: "r1" }, { f: "e5", t: "r2" }, { f: "d2", t: "r3" }, { f: "pay", t: "r4" },
  ],
};

/* ---------------- 流程图中心（13 视图分组导航） ---------------- */
PAGES.flow = async function (box) {
  const sos = await API.list("Sales Order", ["name", "custom_factory_order_no"], [["docstatus", "=", 1]], 10);
  const fo = sos[0]?.custom_factory_order_no;
  let chainHTML = "";
  if (fo) {
    const chain = await buildChain(fo);
    chainHTML = `<div class="flowmap">${CHAIN_STEPS.map((st, i) => {
      const docs = chain.steps[st.key] || [];
      const cls = chainStepState({ docs });
      const main = docs[0];
      return `<div class="fm-node ${cls === "done" ? "done" : ""}" style="animation-delay:${i * 60}ms">
        <span class="fm-step">${String(i + 1).padStart(2, "0")} ${st.label}</span>
        <b>${esc(st.name)}</b>
        ${docs.length ? docs.map(d => `<span class="mono">${esc(d.name)}</span>`).join("") : `<small style="color:var(--faint)">— 无单据 —</small>`}
        <small>${docs.length ? `${docs.length} 张 · ${docs.every(d => d.docstatus === 1) ? "全部已提交" : "含草稿"}` : "待该环节执行"}</small>
        ${main ? `<small>${esc(main.supplier || main.customer || main.purpose || "")}${main.grand_total ? " · " + fmtMoney(main.grand_total) : ""}</small>` : ""}
      </div>`;
    }).join("")}</div>`;
  } else {
    chainHTML = `<div class="card card-bd empty">暂无已提交订单，无法生成链路图</div>`;
  }

  /* 图例与说明（按视图配置） */
  const lg = (pairs) => `<div class="flow-legend">${pairs.map(([c, l]) => `<span><i style="background:${FLOW_COLORS[c][1]}"></i>${l}</span>`).join("")}</div>`;
  const V = {
    main: {
      lg: lg([["blue", "产品数据"], ["purple", "订单处理"], ["orange", "生产执行"], ["green", "采购管理"], ["peach", "仓储质检"], ["yellow", "财务核算"], ["cyan", "辅助支撑"]]),
      cfg: FLOW_MAIN,
      note: "从型体产品库到财务三大报表的全景业务流：BOM 驱动订单用量 → 生产派工 / 采购 → 暂收-检验-入库 → 领料出库 → 应付与成本 → 凭证与报表",
    },
    master: {
      lg: lg([["cyan", "编码上游基础"], ["blue", "编码要素"], ["white", "编码结果"], ["green", "业务应用"], ["yellow", "业务伙伴资料"], ["purple", "系统扩展"], ["gray", "规则资料"]]),
      cfg: FLOW_MASTER,
      note: "四组基础资料为全系统主数据底座；物料编码由「大类 + 品名 + 规格 + 颜色」四要素生成，直达采购管理",
    },
    mes: {
      lg: lg([["blue", "产品数据"], ["white", "订单输入"], ["orange", "计划派工与报工"], ["cyan", "工段SOP与查询"], ["peach", "工序检验"], ["green", "扫描入库"], ["purple", "现场工具"]]),
      cfg: FLOW_MES,
      note: "生管派工下发裁备 / 针车 / 成型 / 其它四条产线，每线走「派工 → 检验 → 报工 → 扫描入库」闭环；PDA / 平板现场作业并打印工艺标签，产量汇聚大屏看板与条码查询中心",
    },
    qc: {
      lg: lg([["white", "订单与派工"], ["cyan", "品检基础"], ["orange", "检验执行"], ["purple", "线上检验"], ["yellow", "品质报表"]]),
      cfg: FLOW_QC,
      note: "依据品检基础资料与工段检验项目执行车间检验，成品验货 / 翻箱 / 送测闭环，检验不良率与 RFT 月统计报表支撑品质改善",
    },
    sfc: {
      lg: lg([["cyan", "基础设置"], ["white", "订单派工"], ["orange", "出入库业务"], ["green", "半成品库存"], ["yellow", "库存报表"]]),
      cfg: FLOW_SFC,
      note: "针车产量录入生成半成品入库，半成品库存统一驱动出库、盘点、调整、结转，进销存与配套报表全程可视",
    },
    fg: {
      lg: lg([["cyan", "仓库与条码查询"], ["white", "订单与出货"], ["orange", "出入库业务"], ["green", "成品库存"], ["purple", "扫描作业"], ["yellow", "应收与报表"]]),
      cfg: FLOW_FG,
      note: "生产入库与出货通知双轨驱动成品库存；订单装箱 / 条码 / 扫描出入库防止错发漏发，出货同步生成应收明细",
    },
    ar: {
      lg: lg([["white", "业务来源"], ["cyan", "应收基础"], ["orange", "应收流程"], ["green", "收支管理"], ["blue", "期初初始化"], ["yellow", "应收报表"]]),
      cfg: FLOW_AR,
      note: "成品 / 样品 / 外卖材料出货统一生成出货应收明细，经对账单与收款单进入收支管理，支持预收、扣款与发票管理",
    },
    ap: {
      lg: lg([["white", "业务来源"], ["cyan", "应付基础"], ["orange", "应付流程"], ["green", "收支管理"], ["blue", "期初初始化"], ["yellow", "应付报表"]]),
      cfg: FLOW_AP,
      note: "委外与验收入库生成应付明细，工厂确认后与供应商对账，付款单进入收支管理，完成厂商对账闭环",
    },
    cost: {
      lg: lg([["white", "业务触发"], ["cyan", "分摊与成控"], ["orange", "核算流程"], ["green", "凭证与锁账"], ["yellow", "标准成本与报表"], ["purple", "异常追踪"]]),
      cfg: FLOW_COST,
      note: "材料加工核销与成本项目归集，成本计算 → 成本结转 → 存货核算 → 销售成本，自动生成凭证并财务锁账",
    },
    asset: {
      lg: lg([["cyan", "基础属性"], ["orange", "资产业务"], ["green", "财务结果"], ["yellow", "追踪报表"]]),
      cfg: FLOW_ASSET,
      note: "资产明细统一驱动领用 / 调动 / 变动 / 维修 / 减少 / 盘点六类业务，折旧自动生成总账凭证",
    },
    gl: {
      lg: lg([["cyan", "基础设置"], ["white", "收付款单"], ["green", "收支与结账"], ["orange", "凭证处理"], ["yellow", "账簿与报表"]]),
      cfg: FLOW_GL,
      note: "收付款与报销汇总生成凭证，审核 → 过账 → 期末调汇 → 损益结转 → 期末结账，输出日记账、明细账与三大报表",
    },
    hr: {
      lg: lg([["cyan", "基础资料"], ["white", "考勤记录"], ["orange", "人事与考勤业务"], ["green", "薪资计算"], ["yellow", "人事报表"]]),
      cfg: FLOW_HR,
      note: "人事档案、考勤、薪资一体化：打卡 / 补卡 / 异常考勤汇总为考勤日报，连同标准工时与调薪明细进入薪资计算",
    },
  };

  /* 分组 Tab 导航 */
  const GROUPS = [
    ["核心链路", [["chain", "指令单链路穿透"], ["main", "ERP 总体业务流程"], ["master", "基础资料与物料编码"]]],
    ["生产管理", [["mes", "生产制造 MES"], ["qc", "品质检验管理"]]],
    ["仓储管理", [["sfc", "半成品库存管理"], ["fg", "成品库存与条码"]]],
    ["财务管理", [["ar", "应收账款"], ["ap", "应付账款"], ["cost", "成本核算"], ["asset", "固定资产"], ["gl", "财务总账"]]],
    ["人力资源", [["hr", "人力资源"]]],
  ];
  const tabsHTML = GROUPS.map(([g, items]) =>
    `<span class="ft-group">${g}</span>` + items.map(([k, t]) => `<button data-tab="${k}">${t}</button>`).join("")).join("");

  box.innerHTML = `
    ${pageHeader("i-link", "流程图中心", "指令单链路穿透 + 生产 / 仓储 / 财务 / 人资全景流程图",
      `<span class="pill run">共 13 张流程图</span>`)}
    <div class="flow-tabs">${tabsHTML}</div>
    <div id="flow-tab-body"></div>`;

  const body = $("#flow-tab-body");
  const renderTab = (tab) => {
    if (tab === "chain") {
      body.innerHTML = `<p class="flow-note" style="text-align:left">指令单 ${esc(fo || "—")} 的 14 步单据链路，金色节点为已完成环节</p>${chainHTML}`;
    } else {
      const v = V[tab] || V.main;
      body.innerHTML = v.lg + flowRender(v.cfg) + `<p class="flow-note">${v.note}</p>`;
    }
    $$(".flow-tabs button").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  };
  renderTab("chain");
  $$(".flow-tabs button").forEach(b => b.addEventListener("click", () => renderTab(b.dataset.tab)));
};

/* ---------------- 全局搜索 ---------------- */
$("#global-search").addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim();
  if (!q) return;
  // 先试指令单号 → 链路抽屉
  const sos = await API.list("Sales Order", ["name"], [["custom_factory_order_no", "=", q]], 5);
  if (sos.length) { openChainDrawer(q); e.target.value = ""; return; }
  // 试单号直接匹配各 doctype
  const types = ["Sales Order", "Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry",
    "Work Order", "Job Card", "Stock Entry", "Subcontracting Order", "Subcontracting Receipt", "Material Request"];
  for (const dt of types) {
    const rows = await API.list(dt, ["name"], [["name", "=", q]], 2);
    if (rows.length) { toast(`已找到单据 ${q}（${dt}），正在打开原单`); openERP(dt, q); e.target.value = ""; return; }
  }
  // 试款号
  const items = await API.list("Item", ["item_code"], [["item_code", "like", `%${q}%`]], 20);
  if (items.length) {
    location.hash = "#/warehouse";
    toast(`找到 ${items.length} 个相关物料，已跳转仓库页`);
    return;
  }
  toast("未找到匹配的单号或指令单号", true);
});

/* ---------------- 导出内联事件所需的全局函数 ---------------- */
window.openChainDrawer = openChainDrawer;
window.openERP = openERP;
window.scanClearLog = scanClearLog;

/* ---------------- 启动 ---------------- */
if (API.token) { enterApp(); } else { showLogin(); }

})();
