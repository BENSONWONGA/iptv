/* ============================================================
   奥登科鞋业 · 中文 ERP 门户  App Logic
   数据层直连 ERPNext REST API（经同域代理 /api → ERPNext）
   ============================================================ */
"use strict";

const COMPANY = "奥登科鞋业有限公司";
/* 预览环境演示令牌（上线部署前请移除） */
const DEMO_TOKEN = "77455c7d4b3a8fe:f36c1a4b10e8b5e";
const WAREHOUSES = {
  "材料仓": "材料仓 - 奥登科",
  "半成品仓": "半成品仓 - 奥登科",
  "委外仓": "委外供应商仓 - 奥登科",
  "在制品": "在制品 - 奥登科",
  "成品仓": "成品仓 - 奥登科",
};
const WH_COLORS = { "材料仓": "#2C5A97", "半成品仓": "#7C5CBF", "委外仓": "#E8871E", "在制品": "#3E8FA3", "成品仓": "#1B7A4B" };

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
    const j = await this.req("POST", "/api/method/frappe.client.submit", { doctype, name });
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
  const base = localStorage.getItem("odk_erp_base") || "";
  if (base) window.open(`${base}/app/${encodeURIComponent(doctype.toLowerCase().replace(/ /g, "-"))}/${encodeURIComponent(name)}`, "_blank");
}

/* ---------------- 登录 ---------------- */
function showLogin() {
  localStorage.removeItem("odk_token");
  $("#app-view").hidden = true;
  $("#login-view").style.display = "flex";
  $("#login-base").value = $("#login-base").value || (location.origin.startsWith("http") ? location.origin : "");
  /* 预览环境：自动填入演示令牌，直接点登录即可 */
  if (!$("#login-token").value) {
    $("#login-token").value = DEMO_TOKEN;
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
    // base 用于展示，API 走同域代理 /api
    const j = await fetch("/api/method/frappe.auth.get_logged_user", {
      headers: { "Authorization": "token " + token, "Accept": "application/json" },
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
  $("#side-user-name").textContent = u === "Administrator" ? "系统管理员" : u;
  $("#side-user-role").textContent = u;
  render();
}

/* ---------------- 路由 ---------------- */
const TITLES = {
  dashboard: "工作台", orders: "指令单中心", purchase: "采购管理", subcontract: "委外加工",
  production: "生产制造", warehouse: "仓库管理", scan: "扫码出入库", finance: "应付对账", flow: "流程链路图",
};
const PAGES = {};
function currentRoute() {
  const h = location.hash.replace(/^#\//, "") || "dashboard";
  return TITLES[h] ? h : "dashboard";
}
async function render() {
  const page = currentRoute();
  $("#crumb").textContent = TITLES[page];
  $$("#nav a").forEach(a => a.classList.toggle("active", a.dataset.page === page));
  const box = $("#page");
  box.innerHTML = skeleton(8);
  try {
    await PAGES[page](box);
  } catch (e) {
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

  // 最近指令单链路进度
  const fo = sos[0]?.custom_factory_order_no || activeSO[0]?.custom_factory_order_no;
  let flowbarHTML = "";
  if (fo) {
    const chain = await buildChain(fo);
    flowbarHTML = `
      <div class="card" style="margin-bottom:14px">
        <div class="card-hd"><h3>指令单 ${esc(fo)} · 流程进度</h3>
          <button class="btn-sm amber" onclick="openChainDrawer('${esc(fo)}')">查看完整链路</button></div>
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
      <b>${k}<small style="color:var(--sub);font-weight:400">（${cnt} 种料件）</small></b>
      <span class="qty">${fmtNum(total)}</span></div>`;
  }).join("");

  box.innerHTML = `
    <div class="page-hd"><h2>早上好，欢迎回来<small>${new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric", weekday: "long" })} · 数据实时同步自 ERPNext</small></h2></div>
    <div class="grid g4" style="margin-bottom:14px">
      <div class="card stat-card"><div class="stat-label">进行中指令单</div>
        <div class="stat-value">${fmtNum(activeSO.length)}<small>单</small></div>
        <div class="stat-foot">累计接单 ${sos.length} 单</div></div>
      <div class="card stat-card"><div class="stat-label">在产工单</div>
        <div class="stat-value">${fmtNum(activeWO.reduce((a, b) => a + (b.qty || 0), 0))}<small>双</small></div>
        <div class="stat-foot">${activeWO.length} 张工单生产中</div></div>
      <div class="card stat-card amber"><div class="stat-label">待付货款</div>
        <div class="stat-value">${fmtNum(unpaidAmt / 10000, 1)}<small>万元</small></div>
        <div class="stat-foot">${unpaid.length} 张发票待付</div></div>
      <div class="card stat-card"><div class="stat-label">成品仓库存</div>
        <div class="stat-value">${fmtNum(fgQty)}<small>双</small></div>
        <div class="stat-foot">即时库存快照</div></div>
    </div>
    ${flowbarHTML}
    <div class="grid g2">
      <div class="card"><div class="card-hd"><h3>待办事项</h3></div>
        <div class="card-bd">${todoRows}</div></div>
      <div class="card"><div class="card-hd"><h3>库存概览</h3></div>
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
    <div class="page-hd"><h2>指令单中心<small>以工厂指令单号为主线，点击行查看全流程链路穿透</small></h2></div>
    <div class="card">
      <div class="card-hd"><h3>订单列表</h3><span style="font-size:12.5px;color:var(--sub)">共 ${rows.length} 单</span></div>
      <table class="tbl">
        <thead><tr><th>指令单号</th><th>销售订单</th><th>客户</th><th>款号明细</th><th>订单金额</th><th>日期</th><th>状态</th><th></th></tr></thead>
        <tbody>${rows.map(so => `
          <tr style="cursor:pointer" onclick="openChainDrawer('${esc(so.custom_factory_order_no || so.name)}')">
            <td><b class="mono" style="color:#0069DB">${esc(so.custom_factory_order_no || "—")}</b></td>
            <td class="mono">${esc(so.name)}</td>
            <td>${esc(so.customer)}</td>
            <td style="font-size:12.5px;color:var(--sub)">${so.items}</td>
            <td class="num">${fmtMoney(so.grand_total)}</td>
            <td class="num">${fmtDate(so.transaction_date)}</td>
            <td>${statusPill(so.status, so.docstatus)}</td>
            <td><button class="btn-sm ghost" onclick="event.stopPropagation();openERP('Sales Order','${esc(so.name)}')">原单</button></td>
          </tr>`).join("") || `<tr><td colspan="8" class="empty">暂无订单</td></tr>`}
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
    <div class="page-hd"><h2>采购管理<small>材料采购订单与到货收料全程跟踪</small></h2></div>
    <div class="grid g2" style="margin-bottom:14px">
      <div class="card"><div class="card-hd"><h3>供应商（${sups.length}）</h3></div><div class="card-bd" style="padding:8px 18px">
        ${sups.map(s => `<div class="wh-chip"><span class="dot" style="background:${s.supplier_group === "委外加工厂" ? "#E8871E" : "#2C5A97"}"></span>
          <b>${esc(s.supplier_name)}<small style="color:var(--sub);font-weight:400;margin-left:6px">${esc(s.supplier_group || "")}</small></b></div>`).join("")}
      </div></div>
      <div class="card"><div class="card-hd"><h3>采购概览</h3></div><div class="card-bd">
        <div class="wh-chip"><span class="dot" style="background:#2C5A97"></span><b>采购订单总数</b><span class="qty">${pos.length}</span></div>
        <div class="wh-chip"><span class="dot" style="background:#1B7A4B"></span><b>已到货收料</b><span class="qty">${prs.length}</span></div>
        <div class="wh-chip"><span class="dot" style="background:#E8871E"></span><b>采购总额</b><span class="qty">${fmtMoney(pos.reduce((a, b) => a + (b.grand_total || 0), 0))}</span></div>
      </div></div>
    </div>
    <div class="card" style="margin-bottom:14px">
      <div class="card-hd"><h3>采购订单</h3></div>
      <table class="tbl"><thead><tr><th>订单号</th><th>供应商</th><th>指令单</th><th>金额</th><th>日期</th><th>状态</th><th></th></tr></thead>
      <tbody>${pos.map(p => `<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.supplier)}</td>
        <td class="mono">${esc(p.custom_factory_order_no || "—")}</td><td class="num">${fmtMoney(p.grand_total)}</td>
        <td class="num">${fmtDate(p.transaction_date)}</td><td>${statusPill(p.status, p.docstatus)}</td>
        <td><button class="btn-sm ghost" onclick="openERP('Purchase Order','${esc(p.name)}')">原单</button></td></tr>`).join("")}
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
    <div class="page-hd"><h2>委外加工<small>发料给委外厂 → 帮面收货 → 加工费结算</small></h2></div>
    <div class="grid g3" style="margin-bottom:14px">
      <div class="card stat-card"><div class="stat-label">委外订单</div><div class="stat-value">${scos.length}<small>单</small></div></div>
      <div class="card stat-card"><div class="stat-label">累计发料</div><div class="stat-value">${seOut.length}<small>笔</small></div></div>
      <div class="card stat-card"><div class="stat-label">帮面到货</div><div class="stat-value">${scrs.length}<small>单</small></div></div>
    </div>
    <div class="card" style="margin-bottom:14px">
      <div class="card-hd"><h3>委外订单（SCO）</h3></div>
      <table class="tbl"><thead><tr><th>委外单号</th><th>委外厂</th><th>指令单</th><th>日期</th><th>状态</th><th></th></tr></thead>
      <tbody>${scos.map(s => `<tr><td class="mono">${esc(s.name)}</td><td>${esc(s.supplier)}</td>
        <td class="mono">${esc(s.custom_factory_order_no || "—")}</td><td class="num">${fmtDate(s.transaction_date)}</td>
        <td>${statusPill(s.status, s.docstatus)}</td>
        <td><button class="btn-sm ghost" onclick="openERP('Subcontracting Order','${esc(s.name)}')">原单</button></td></tr>`).join("")}
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
    <div class="page-hd"><h2>生产制造<small>工单进度与 MES 工序报工</small></h2></div>
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
          <div style="height:10px;background:#EDF1F7;border-radius:5px;overflow:hidden;margin-bottom:6px">
            <div style="width:${pct}%;height:100%;background:${done ? "linear-gradient(180deg,#4BE37D,#1FA848)" : "linear-gradient(180deg,#FFC24A,#F07F00)"};border-radius:5px;transition:width .6s;box-shadow:inset 0 1px 0 rgba(255,255,255,.45)"></div></div>
          <div style="display:flex;justify-content:space-between;font-size:12.5px">
            <span style="color:var(--sub)">计划 <b class="num" style="color:var(--ink)">${fmtNum(w.qty)}</b> 双</span>
            <span style="color:var(--sub)">已入库 <b class="num" style="color:${done ? "#1D8A3E" : "#C24F00"}">${fmtNum(w.produced_qty || 0)}</b> 双（${pct}%）</span>
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
    <div class="page-hd"><h2>仓库管理<small>五大仓位实时库存 · 扫码出入库请用左侧「扫码出入库」</small></h2></div>
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
    <div class="page-hd"><h2>扫码出入库<small>USB 扫码枪即扫即录 · 自动创建库存调拨单并提交</small></h2></div>
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
    <div class="page-hd"><h2>应付对账<small>供应商开票、付款与往来余额一表看清</small></h2></div>
    <div class="grid g3" style="margin-bottom:14px">
      <div class="card stat-card"><div class="stat-label">累计开票</div><div class="stat-value">${fmtNum(totalInv / 10000, 1)}<small>万元</small></div></div>
      <div class="card stat-card"><div class="stat-label">累计付款</div><div class="stat-value">${fmtNum(totalPay / 10000, 1)}<small>万元</small></div></div>
      <div class="card stat-card amber"><div class="stat-label">未结清余额</div><div class="stat-value">${fmtNum(rows.reduce((a, r) => a + r.bal, 0) / 10000, 2)}<small>万元</small></div></div>
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

/* ---------------- 流程链路图 ---------------- */
PAGES.flow = async function (box) {
  const sos = await API.list("Sales Order", ["name", "custom_factory_order_no"], [["docstatus", "=", 1]], 10);
  const fo = sos[0]?.custom_factory_order_no;
  if (!fo) { box.innerHTML = `<div class="card card-bd empty">暂无已提交订单，无法生成链路图</div>`; return; }
  const chain = await buildChain(fo);
  const nodes = CHAIN_STEPS.map((st, i) => {
    const docs = chain.steps[st.key] || [];
    const cls = chainStepState({ docs });
    const main = docs[0];
    return `<div class="fm-node ${cls === "done" ? "done" : ""}" style="animation-delay:${i * 60}ms">
      <span class="fm-step">${String(i + 1).padStart(2, "0")} ${st.label}</span>
      <b>${esc(st.name)}</b>
      ${docs.length ? docs.map(d => `<span class="mono">${esc(d.name)}</span>`).join("") : `<small style="color:#C3CEDD">— 无单据 —</small>`}
      <small>${docs.length ? `${docs.length} 张 · ${docs.every(d => d.docstatus === 1) ? "全部已提交" : "含草稿"}` : "待该环节执行"}</small>
      ${main ? `<small>${esc(main.supplier || main.customer || main.purpose || "")}${main.grand_total ? " · " + fmtMoney(main.grand_total) : ""}</small>` : ""}
    </div>`;
  }).join("");
  box.innerHTML = `
    <div class="page-hd"><h2>流程链路图<small>指令单 ${esc(fo)}：从接单到付款的 14 步全流程穿透</small></h2></div>
    <div class="flowmap">${nodes}</div>`;
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
    if (rows.length) { toast(`在「${TITLES[Object.keys(TITLES)[0]]}」找到 ${dt}: ${q}`); openERP(dt, q); e.target.value = ""; return; }
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

/* ---------------- 启动 ---------------- */
if (API.token) { enterApp(); } else { showLogin(); }
