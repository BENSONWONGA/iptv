/* 鞋企 ERP 全流程验收报告生成 */
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
  VerticalAlign,
} = require("docx");

// ===== 通用样式常量 =====
const FONT = { ascii: "Arial", hAnsi: "Arial", eastAsia: "Microsoft YaHei" };
const INK = "1F2937";
const ACCENT = "0A7A66";
const GRAY = "6B7280";
const LINE = "D1D5DB";
const HEAD_BG = "E6F2EF";
const ZEBRA = "F7FAF9";

const border = { style: BorderStyle.SINGLE, size: 1, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 70, bottom: 70, left: 110, right: 110 };

// 内容宽度 A4 - 2×1.25in 边距 = 11906 - 3600 = 8306... 用 9026(1in边距)
const CW = 9026;

// ===== 辅助函数 =====
const t = (text, opts = {}) => new TextRun({ text, font: FONT, size: 21, color: INK, ...opts });

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 320, after: 160 },
  children: [t(text, { size: 30, bold: true, color: ACCENT })],
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 240, after: 120 },
  children: [t(text, { size: 24, bold: true, color: INK })],
});

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: 100, line: 320 },
  alignment: AlignmentType.JUSTIFIED,
  children: [t(text, opts)],
});

const pMixed = (runs) => new Paragraph({
  spacing: { after: 100, line: 320 },
  alignment: AlignmentType.JUSTIFIED,
  children: runs,
});

const bullet = (text, boldPrefix) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 60, line: 300 },
  children: boldPrefix
    ? [t(boldPrefix, { bold: true }), t(text)]
    : [t(text)],
});

// 单元格
function cell(content, opts = {}) {
  const runs = Array.isArray(content) ? content : [t(content, opts.run || {})];
  return new TableCell({
    borders,
    width: { size: opts.w, type: WidthType.DXA },
    margins: cellMargins,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { after: 0, line: 280 },
      children: runs,
    })],
  });
}

// 表头行
function headerRow(labels, widths) {
  return new TableRow({
    cantSplit: true,
    tableHeader: true,
    children: labels.map((l, i) => cell(l, {
      w: widths[i], fill: HEAD_BG, align: AlignmentType.CENTER,
      run: { bold: true, size: 20 },
    })),
  });
}

// 数据行
function dataRow(cells, widths, zebra) {
  return new TableRow({
    cantSplit: true,
    children: cells.map((c, i) => {
      const cfg = typeof c === "object" && c !== null && !Array.isArray(c) ? c : { text: String(c) };
      return cell(cfg.runs || [t(cfg.text, cfg.run || {})], {
        w: widths[i],
        fill: zebra ? ZEBRA : undefined,
        align: cfg.align,
      });
    }),
  });
}

// 通用表格
function table(widths, rows) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows,
  });
}

const spacer = () => new Paragraph({ spacing: { after: 60 }, children: [] });

// ===== 表格数据 =====

// 环境表
const envW = [2200, 6826];
const envRows = [
  ["ERP 平台", "Odoo 20 社区版（Odoo 20.0.1.0）"],
  ["服务器", "220.162.99.166:9000（宝塔托管，systemd 服务 odoo20）"],
  ["数据库", "PostgreSQL · 库名 benson"],
  ["公司主体", "晋江市奥登科鞋业有限公司"],
  ["业务范畴", "户外鞋研发、制造与销售（奥登科 ADK 品牌，12 款产品）"],
  ["验收日期", "2026 年 10 月 13 日"],
  ["验收方式", "RPC 接口逐单核验 + 浏览器界面抽检"],
];

// 核心模块表
const modW = [2600, 1300, 5126];
const modRows = [
  ["销售管理 sale_management", "已安装", "报价 / 订单 / 出库 / 开票"],
  ["采购管理 purchase", "已安装", "询价 / 采购 / 收货 / 账单"],
  ["制造管理 mrp", "已安装", "BOM / 制造订单 / 工作中心 / 工序"],
  ["库存管理 stock", "已安装", "收发货 / 调拨 / 批次 / 补货规则"],
  ["财务管理 account + l10n_cn", "已安装", "中国本地化科目、13% 增值税"],
  ["人力资源 hr / hr_expense", "已安装", "92 名员工档案与费用"],
  ["外协加工 mrp_subcontracting", "已安装", "工序外发管理"],
  ["质量管理 shoe_qms（自研）", "20.0.1.0.0", "IQC / IPQC / FQC / OQC + NCR 处置"],
  ["研发管理 shoe_plm（自研）", "20.0.1.0.0", "ECO 工程变更审批与 BOM 版本管理"],
];

// 基础数据表
const baseW = [2400, 1600, 5026];
const baseRows = [
  ["产品物料清单（BOM）", "13 套", "12 款奥登科成品鞋 + 1 款男士休闲皮鞋全部建档，含 140 条材料行、70 道工序（裁断→针车→绷帮成型→底部加工→包装）"],
  ["产品分类", "19 个", "成品鞋 + 材料总表（皮料 / 布料 / 底料 / 辅料 / 针辅 / 化学品 / 包装类 / 刀模制具）"],
  ["业务伙伴角色", "供应商 34 家 / 客户 32 家", "按皮料、鞋材、化工等供应类别与客户类别完成标记"],
  ["增值税率", "13%", "由默认 15% 修正为中国增值税标准税率，销项 / 进项同步"],
  ["再订货规则", "11 条", "皮料、大底、中底等关键材料设置最低 100 / 最高 500 自动补货点"],
  ["工作中心与工序", "5 + 5", "裁断车间、针车一线、成型一线、底部压合组、包装组"],
];

// 端到端主表
const flowW = [1000, 1500, 3800, 1700, 1026];
const flowHeader = ["阶段", "单据编号", "业务内容", "执行结果", "状态"];
const flowRows = [
  ["1. 销售接单", "S00001", "客户「曾春香」订购 奥登科·征途Pro 中帮徒步鞋（ADK-H001）× 30 双，含税 ¥23,696.10", "订单确认，交付状态：全部交付", "通过"],
  ["2. 生产计划", "WH/MO/00002", "按 BOM-ADK-H001 展开生产 30 双：10 种材料 + 5 道工序自动生成", "制造完成 30/30 双，成品入库 36 双", "通过"],
  ["3. 缺料分析", "—", "MRP 组件可用性核对：头层牛皮、针织内里布、橡胶大底、EVA 中底、乳胶鞋垫、水性胶水、缝纫线、鞋带、鞋盒共 9 种材料缺料", "缺料清单输出，进入采购", "通过"],
  ["4. 采购补料", "P00001", "温州宏达皮革有限公司：牛皮、内里布、缝纫线、鞋带 4 种，¥1,528.89", "已采购", "通过"],
  ["", "P00002", "晋江华利鞋材有限公司：橡胶大底、EVA 中底、乳胶鞋垫、鞋盒 4 种，¥3,169.65", "已采购", "通过"],
  ["", "P00003", "广州港汇贸易有限公司：环保水性胶水 1 种，¥208.82", "已采购", "通过"],
  ["5. 收货入库", "WH/IN/00001~00003", "三张收货单对应三家供应商到料", "全部完成（done）", "通过"],
  ["6. 来料检验 IQC", "QC/2026/0001~0009", "9 张检验单，检验项：外观、尺寸、材质、数量、环保报告（5 项 / 单）", "9/9 全部合格", "通过"],
  ["7. 制程检验 IPQC", "QC/2026/0010", "首件确认、针距线迹、帮面成型、胶合强度、中底大底贴合（5 项）", "合格，允许批量生产", "通过"],
  ["8. 完工报工", "WH/MO/00002", "裁断→针车→绷帮→底部→包装 全工序完工", "材料预留 → 消耗 → 产出 30 双", "通过"],
  ["9. 成品检验 FQC", "QC/2026/0011", "外观全检、左右脚配对、尺码核对、内部清洁、包装标识（5 项）", "合格", "通过"],
  ["10. 出货检验 OQC", "QC/2026/0014", "装箱数量、外箱标识、AQL 抽检、条码扫描（4 项）", "合格（重跑遗留 2 张已作废）", "通过"],
  ["11. 出库交付", "WH/OUT/00001", "30 双发货出库", "完成（done）", "通过"],
  ["12. 销售开票", "INV/2026/00001", "销售发票 ¥23,696.10，13% 增值税", "已过账（posted）", "通过"],
  ["13. 收款核销", "—", "银行收款登记并核销应收账款", "已付款（paid），余额 ¥0.00", "通过"],
  ["14. 工程变更 PLM", "ECO/2026/0003", "「云驰鞋面升级：普通网布→高透气飞织」材料替代变更", "草稿→评审→批准→执行，新版本 BOM 自动克隆生效", "通过"],
];

// 质量检验统计
const qcW = [2200, 1500, 5326];
const qcRows = [
  ["IQC 来料检验", "9 张", "QC/2026/0001~0009，9 种材料全部合格"],
  ["IPQC 制程检验", "1 张", "QC/2026/0010，首件 + 四大制程关键点合格"],
  ["FQC 成品检验", "1 张", "QC/2026/0011，五项成品全检合格"],
  ["OQC 出货检验", "1 张有效", "QC/2026/0014 合格；00012/00013 为流程重跑遗留，已作废处理"],
  ["NCR 不合格处置", "0 张", "本次全流程未触发不合格品（处置功能已具备：返工 / 让步接收 / 报废 / 退货 / 挑选）"],
];

// 单据总量核验
const statW = [3000, 1500, 4526];
const statRows = [
  ["销售订单 sale.order", "1", "S00001，状态 sale（已确认）"],
  ["采购订单 purchase.order", "3", "P00001~P00003，状态 purchase（已采购）"],
  ["制造订单 mrp.production", "2", "MO/00002 完成；MO/00001 为建单测试已作废"],
  ["库存调拨 stock.picking", "4", "3 收货 + 1 出库，全部 done"],
  ["会计凭证 account.move", "3", "销售发票 1 张（posted/paid）+ 收款凭证"],
  ["质量检验单 qc.inspection", "14", "IQC 9 / IPQC 1 / FQC 1 / OQC 3（含 2 张作废）"],
  ["工程变更单 plm.eco", "2", "ECO/0003 已执行；ECO/0002 为演示遗留已取消"],
  ["BOM / 材料行 / 工序", "13 / 140 / 70", "13 款成品鞋全覆盖"],
  ["再订货规则 orderpoint", "11", "关键材料自动补货"],
  ["业务伙伴 res.partner", "99", "供应商 34 / 客户 32 / 其他 33"],
];

// 问题记录
const issueW = [2700, 3400, 2926];
const issueRows = [
  ["RPC 创建 MO 不加载 BOM", "接口创建不触发界面 onchange，制造订单组件为空", "显式传入 bom_id 重建 MO，组件与工序正确展开"],
  ["私有方法禁止远程调用", "Odoo 20 安全限制，_create_invoices 等无法经 RPC 调用", "改为手工创建发票字段 + account.payment.register 标准向导开票收款"],
  ["BOM 复制接口变更", "copy() 不再接受 default_ 前缀参数", "先 copy 后 write 指定产品与编码"],
  ["BOM 归档被订单锁定", "销售订单行引用的 BOM 不允许归档（数据保护）", "PLM 变更演示切换至无订单占用的产品（ADK-T002 云驰）执行"],
  ["Odoo 20 字段变更", "consumption、product_uom_id、worksheet_type 等字段已更名或移除", "按新版字段清单逐项适配接口调用"],
  ["补货路线限制", "仓库级 Manufacture 路由不可直接挂到产品 / 分类", "采用手动 MO + 组件缺料采购模式，符合鞋厂按单生产实际"],
];

// ===== 文档组装 =====
const children = [];

// 封面
children.push(new Paragraph({ spacing: { before: 2200, after: 0 }, children: [] }));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 200 },
  children: [t("晋江市奥登科鞋业有限公司", { size: 26, color: GRAY })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [t("鞋企 ERP 全流程跑通验收报告", { size: 52, bold: true, color: ACCENT })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 1800 },
  children: [t("Sales · Purchasing · IQC · Manufacturing · IPQC / FQC · Delivery · Invoicing · PLM", { size: 20, color: GRAY })],
}));
children.push(table(envW, [
  headerRow(["项目", "内容"], envW),
  ...envRows.map((r, i) => dataRow(r, envW, i % 2 === 1)),
]));
children.push(new Paragraph({
  spacing: { before: 1600 },
  alignment: AlignmentType.CENTER,
  children: [t("验收结论：通过", { size: 36, bold: true, color: ACCENT })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 120 },
  children: [t("2026 年 10 月 13 日", { size: 22, color: GRAY })],
}));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 一、验收概况
children.push(h1("一、验收概况"));
children.push(p("本验收针对奥登科鞋业 ERP 系统的全业务流程闭环能力。系统基于 Odoo 20 社区版部署，覆盖鞋企从销售接单、生产计划、物料采购、来料检验、制造执行、制程与成品检验、出货检验、库存交付、财务开票收款，到研发工程变更（PLM）的完整价值链。"));
children.push(pMixed([
  t("本次验收以 "),
  t("一张真实销售订单（S00001）为主线", { bold: true }),
  t("，端到端驱动全部 14 个业务环节，产生真实业务单据并逐单核验状态，验证系统流程的完整性与数据一致性。验收范围包括：自研模块部署（shoe_plm / shoe_qms）、基础数据完善（BOM / 伙伴 / 税率 / 补货规则）、端到端流程执行与财务闭环核验。"),
]));
children.push(spacer());
children.push(table([2200, 6826], [
  headerRow(["验收项", "结论"], [2200, 6826]),
  dataRow(["自研模块部署", "通过"], [2200, 6826]),
  dataRow(["基础数据完善", "通过"], [2200, 6826], true),
  dataRow(["端到端流程执行（14 环节）", "通过"], [2200, 6826]),
  dataRow(["财务闭环（开票→收款核销）", "通过"], [2200, 6826], true),
  dataRow(["PLM 工程变更闭环", "通过"], [2200, 6826]),
]));

// 二、验收环境
children.push(h1("二、验收环境与系统配置"));
children.push(table(envW, [
  headerRow(["项目", "内容"], envW),
  ...envRows.map((r, i) => dataRow(r, envW, i % 2 === 1)),
]));
children.push(spacer());
children.push(h2("核心业务模块"));
children.push(table(modW, [
  headerRow(["模块", "版本 / 状态", "功能范围"], modW),
  ...modRows.map((r, i) => dataRow(r, modW, i % 2 === 1)),
]));
children.push(p("说明：工单级管理（mrp_workorder）、官方质量模块（quality_control）、官方 PLM（mrp_plm）、条码（stock_barcode）为 Odoo 企业版付费功能，社区版不可用；质量与研发管理需求已由自研模块 shoe_qms、shoe_plm 覆盖。", { color: GRAY, size: 19 }));

// 三、自研模块
children.push(h1("三、自研模块部署验收"));
children.push(h2("3.1 鞋厂质量管理 shoe_qms"));
children.push(bullet("四级检验体系：来料 IQC / 制程 IPQC / 成品 FQC / 出货 OQC，内置鞋业标准检验项模板，创建检验单时自动填充。", "检验类型："));
children.push(bullet("不合格品处置单 NCR：支持返工、让步接收、报废、退货、挑选五种处置方式，可由不合格检验单一键生成。", "处置能力："));
children.push(bullet("与库存调拨单、生产工单、批次关联，检验员、供应商、检验标准、实测结果、逐项判定全程留痕。", "关联集成："));
children.push(h2("3.2 鞋厂研发管理 shoe_plm"));
children.push(bullet("工程变更单 ECO：设计变更 / 工艺变更 / 材料替代 / 图纸纠错四类，完整审批流（草稿→评审→批准→执行）。", "变更类型："));
children.push(bullet("执行变更时自动克隆生成新版本 BOM 并归档旧版本，版本血缘可追溯；BOM 表单可查看关联变更历史。", "版本管理："));
children.push(bullet("技术图纸与资料附件管理，申请、批准、执行人及时间全程跟踪。", "资料管理："));
children.push(p("部署结果：两模块均以 20.0.1.0.0 版本安装成功，菜单「质量管理」「研发管理」已在后台正常呈现，权限组与单据序列（QC/2026/xxxx、ECO/2026/xxxx）配置生效。"));

// 四、基础数据
children.push(h1("四、基础数据完善验收"));
children.push(p("验收前系统仅有 1 套 BOM、零业务伙伴角色、默认 15% 税率，不具备下单条件。完善后主数据如下："));
children.push(table(baseW, [
  headerRow(["数据项", "数量", "说明"], baseW),
  ...baseRows.map((r, i) => dataRow(r, baseW, i % 2 === 1)),
]));

// 五、端到端流程
children.push(h1("五、端到端全流程验收（核心）"));
children.push(p("以销售订单 S00001 为主线，完整执行「接单→生产→采购→检验→交付→收款→变更」全链路，各环节单据与核验结果如下："));
children.push(table(flowW, [
  headerRow(flowHeader, flowW),
  ...flowRows.map((r, i) => dataRow(r, flowW, i % 2 === 1)),
]));
children.push(spacer());
children.push(h2("5.1 质量检验明细"));
children.push(table(qcW, [
  headerRow(["检验类型", "数量", "明细与结论"], qcW),
  ...qcRows.map((r, i) => dataRow(r, qcW, i % 2 === 1)),
]));
children.push(h2("5.2 资金闭环"));
children.push(pMixed([
  t("销售发票 "),
  t("INV/2026/00001", { bold: true }),
  t(" 金额 ¥23,696.10（30 双 × ¥789.87，含 13% 增值税），经银行收款登记并核销后，发票状态为 "),
  t("posted / paid，未清余额 ¥0.00", { bold: true }),
  t("，应收账款完成闭环。"),
]));

// 六、数据核验
children.push(h1("六、系统数据核验"));
children.push(p("验收结束后通过 Odoo RPC 接口对全部业务单据进行权威状态核验（非界面目测），结果如下："));
children.push(table(statW, [
  headerRow(["单据类型", "数量", "状态核验"], statW),
  ...statRows.map((r, i) => dataRow(r, statW, i % 2 === 1)),
]));
children.push(p("关键状态核验：S00001 state=sale、交付状态=全部交付；WH/MO/00002 state=done（30/30 双）；INV/2026/00001 state=posted、payment_state=paid；三张采购单 state=purchase；四张调拨单全部 done。", { color: GRAY, size: 19 }));

// 七、问题记录
children.push(h1("七、问题与解决记录"));
children.push(p("实施与验收过程中发现并已解决的技术问题："));
children.push(table(issueW, [
  headerRow(["问题", "现象", "解决方案"], issueW),
  ...issueRows.map((r, i) => dataRow(r, issueW, i % 2 === 1)),
]));

// 八、遗留事项
children.push(h1("八、遗留事项与建议"));
children.push(bullet("OQC 检验单 QC/2026/0012、0013 为流程重跑遗留，已作废处理，不影响账实；制造订单 WH/MO/00001、变更单 ECO/2026/0002 为建单测试，已作废 / 取消。", "测试遗留数据："));
children.push(bullet("企业版专属功能（工单级报工、官方质量 / PLM、条码扫描）社区版不可用；如后续需要车间工单级管控与扫码作业，可升级企业版或继续扩展自研模块。", "企业版功能："));
children.push(bullet("当前检验结论由管理员代录；建议为 IQC / IPQC / FQC 检验员分配 shoe_qms 对应权限组，实现岗位分工。", "权限分工："));
children.push(bullet("现有 13 套 BOM 沿用统一标准材料结构，正式投产前建议按各款式实际用料（如 GTX 面料、 Vibram 大底等差异件）逐款细化。", "BOM 精细化："));
children.push(bullet("电商前台（奥登科商城）与本流程共用同一数据库，前台下单可直接进入本验收的销售→生产链路；建议上线前做一次前台真实下单联动测试。", "前后台联动："));

// 九、验收结论
children.push(h1("九、验收结论"));
children.push(pMixed([
  t("经端到端真实单据验证：销售订单 S00001 全线驱动 "),
  t("14 个业务环节全部通过", { bold: true, color: ACCENT }),
  t("，产生 1 张销售订单、3 张采购订单、2 张制造订单、4 张库存调拨、14 张质量检验单（IQC 9 / IPQC 1 / FQC 1 / OQC 3）、1 张已收讫发票及 1 张已执行工程变更单；资金闭环完成（发票 posted / paid，余额为零）；自研质量管理与研发管理模块功能与流程符合鞋企业务要求。"),
]));
children.push(pMixed([
  t("综合结论：", { bold: true }),
  t("奥登科鞋业 ERP 系统"),
  t("全流程跑通验收通过", { bold: true, color: ACCENT }),
  t("，具备承接真实业务的条件。"),
]));

// 签字栏
children.push(spacer());
children.push(spacer());
children.push(table([2833, 2833, 3360], [
  new TableRow({
    cantSplit: true,
    children: [
      cell([t("验收方代表", { bold: true, size: 20 })], { w: 2833, fill: HEAD_BG, align: AlignmentType.CENTER }),
      cell([t("实施方代表", { bold: true, size: 20 })], { w: 2833, fill: HEAD_BG, align: AlignmentType.CENTER }),
      cell([t("日期", { bold: true, size: 20 })], { w: 3360, fill: HEAD_BG, align: AlignmentType.CENTER }),
    ],
  }),
  new TableRow({
    cantSplit: true,
    height: { value: 900, rule: "atLeast" },
    children: [
      cell([t("", { size: 20 })], { w: 2833 }),
      cell([t("", { size: 20 })], { w: 2833 }),
      cell([t("2026 年 10 月 13 日", { size: 20 })], { w: 3360, align: AlignmentType.CENTER }),
    ],
  }),
]));

// ===== 文档 =====
const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: FONT, size: 21, color: INK },
        paragraph: { spacing: { line: 320 } },
      },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: ACCENT, font: FONT },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0, keepNext: false, keepLines: false } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: INK, font: FONT },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1, keepNext: false, keepLines: false } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 620, hanging: 320 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 }, // A4
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE } },
          children: [t("奥登科鞋业 ERP 全流程验收报告", { size: 17, color: GRAY })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            t("第 ", { size: 17, color: GRAY }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 17, color: GRAY }),
            t(" 页", { size: 17, color: GRAY }),
          ],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("/workspace/鞋企ERP全流程验收报告.docx", buffer);
  console.log("生成完成: /workspace/鞋企ERP全流程验收报告.docx");
  console.log(`大小: ${(buffer.length / 1024).toFixed(1)} KB`);
});
