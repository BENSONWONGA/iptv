#!/bin/bash
# Liquid Glass 主题：深色 → 灰白浅色 一键转换
set -e
cd /opt/odoo20/addons/theme_liquid_glass/static/src/scss

F="glass_theme.scss navbar.scss modals.scss lists.scss website.scss forms.scss buttons.scss kanban.scss"

# ---------- 1. 背景图 → 浅灰渐变 ----------
sed -i 's|url("/theme_liquid_glass/static/src/img/bg-img.svg") no-repeat center center fixed|linear-gradient(135deg, #f5f6f8 0%, #e9edf2 100%)|g' $F

# ---------- 2. 白色文字 → 深灰（注意顺序：ffffff → ffff → fff） ----------
sed -i 's/color: #ffffff/color: #2d3a4a/g' $F
sed -i 's/color: #ffff/color: #2d3a4a/g' $F
sed -i 's/color: #fff/color: #2d3a4a/g' $F
sed -i 's/color: white/color: #2d3a4a/g' $F
sed -i 's/caret-color: white/caret-color: #2d3a4a/g' $F
sed -i 's/-webkit-text-fill-color: #ffffff/-webkit-text-fill-color: #2d3a4a/g' $F
sed -i 's/color: rgba(255, 255, 255,/color: rgba(45, 58, 74,/g' $F
sed -i 's/-webkit-text-fill-color: rgba(255, 255, 255,/-webkit-text-fill-color: rgba(45, 58, 74,/g' $F

# ---------- 3. 深色背景 → 白色系 ----------
sed -i 's/background: rgba(10, 16, 28, 0.92)/background: rgba(255, 255, 255, 0.95)/g' $F
sed -i 's/background: rgba(20, 32, 50, 0.97)/background: rgba(255, 255, 255, 0.97)/g' $F
sed -i 's/background: rgba(20, 25, 35, 0.98)/background: rgba(255, 255, 255, 0.98)/g' $F
sed -i 's/background: rgba(73, 70, 70, 0.58)/background: rgba(255, 255, 255, 0.98)/g' $F
sed -i 's/background: #202733/background: #ffffff/g' $F
sed -i 's/background: rgba(8, 16, 30, 0.55)/background: rgba(255, 255, 255, 0.78)/g' $F

# ---------- 4. 白色半透明覆盖背景 → 深色微透明（浅底上的 hover/层次） ----------
sed -i 's/background: rgba(255, 255, 255, 0.06)/background: rgba(0, 0, 0, 0.035)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.07)/background: rgba(0, 0, 0, 0.04)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.08)/background: rgba(0, 0, 0, 0.04)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.1)/background: rgba(0, 0, 0, 0.05)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.10)/background: rgba(0, 0, 0, 0.05)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.12)/background: rgba(0, 0, 0, 0.06)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.13)/background: rgba(0, 0, 0, 0.065)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.14)/background: rgba(0, 0, 0, 0.07)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.15)/background: rgba(0, 0, 0, 0.05)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.18)/background: rgba(0, 0, 0, 0.05)/g' $F
sed -i 's/background: rgba(255, 255, 255, 0.25)/background: rgba(0, 0, 0, 0.08)/g' $F
sed -i 's/background-color: rgba(255, 255, 255, 0.2)/background-color: rgba(0, 0, 0, 0.05)/g' $F
sed -i 's/background-color: rgba(255, 255, 255, 0.18)/background-color: rgba(0, 0, 0, 0.05)/g' $F
sed -i 's/background-color: rgba(255, 255, 255, 0.10)/background-color: rgba(0, 0, 0, 0.04)/g' $F

# ---------- 5. 白色边框 → 深色微透明 ----------
sed -i 's/border: 1px solid rgba(255, 255, 255, 0.1)/border: 1px solid rgba(0, 0, 0, 0.07)/g' $F
sed -i 's/border: 1px solid rgba(255, 255, 255, 0.12)/border: 1px solid rgba(0, 0, 0, 0.08)/g' $F
sed -i 's/border: 1px solid rgba(255, 255, 255, 0.15)/border: 1px solid rgba(0, 0, 0, 0.10)/g' $F
sed -i 's/border: 1px solid rgba(255, 255, 255, 0.2)/border: 1px solid rgba(0, 0, 0, 0.12)/g' $F
sed -i 's/border: 1px solid rgba(255, 255, 255, 0.25)/border: 1px solid rgba(0, 0, 0, 0.15)/g' $F
sed -i 's/border: 2px solid rgba(255, 255, 255, 0.6)/border: 2px solid rgba(0, 0, 0, 0.30)/g' $F
sed -i 's/border: 1.5px solid rgba(255, 255, 255, 0.7)/border: 1.5px solid rgba(0, 0, 0, 0.35)/g' $F
sed -i 's/border-bottom: 1px solid rgba(255, 255, 255, 0.1)/border-bottom: 1px solid rgba(0, 0, 0, 0.07)/g' $F
sed -i 's/border-bottom: 1px solid rgba(255, 255, 255, 0.35)/border-bottom: 1px solid rgba(0, 0, 0, 0.12)/g' $F
sed -i 's/border-bottom: 1px solid rgba(255, 255, 255, 0.12)/border-bottom: 1px solid rgba(0, 0, 0, 0.08)/g' $F
sed -i 's/border-top: 1px solid rgba(255, 255, 255, 0.1)/border-top: 1px solid rgba(0, 0, 0, 0.07)/g' $F
sed -i 's/border-top: 1px solid rgba(255, 255, 255, 0.12)/border-top: 1px solid rgba(0, 0, 0, 0.08)/g' $F
sed -i 's/border-right: 1px solid rgba(255, 255, 255, 0.12)/border-right: 1px solid rgba(0, 0, 0, 0.08)/g' $F
sed -i 's/border-left: 1px solid rgba(255, 255, 255, 0.12)/border-left: 1px solid rgba(0, 0, 0, 0.08)/g' $F
sed -i 's/border-color: rgba(255, 255, 255, 0.2)/border-color: rgba(0, 0, 0, 0.12)/g' $F
sed -i 's/border-color: rgba(255, 255, 255, 0.25)/border-color: rgba(0, 0, 0, 0.15)/g' $F
sed -i 's/border-color: rgba(255, 255, 255, 0.5)/border-color: rgba(0, 0, 0, 0.2)/g' $F

# ---------- 6. CSS 变量 ----------
sed -i 's/--NavBar-entry-backgroundColor--hover: rgba(255, 255, 255, 0.1)/--NavBar-entry-backgroundColor--hover: rgba(0, 0, 0, 0.06)/g' $F
sed -i 's/--NavBar-entry-backgroundColor--focus: rgba(255, 255, 255, 0.1)/--NavBar-entry-backgroundColor--focus: rgba(0, 0, 0, 0.06)/g' $F
sed -i 's/--NavBar-entry-backgroundColor--active: rgba(255, 255, 255, 0.15)/--NavBar-entry-backgroundColor--active: rgba(0, 0, 0, 0.09)/g' $F
sed -i 's/--btn-border-color: rgba(255, 255, 255, 0.2)/--btn-border-color: rgba(0, 0, 0, 0.12)/g' $F
sed -i 's/--btn-hover-border-color: rgba(255, 255, 255, 0.4)/--btn-hover-border-color: rgba(0, 0, 0, 0.25)/g' $F
sed -i 's/--mail-DiscussSearch-inputBgColor: rgba(255, 255, 255, 0.06)/--mail-DiscussSearch-inputBgColor: rgba(0, 0, 0, 0.04)/g' $F
sed -i 's/--alert-border-color: rgba(255, 255, 255, 0.18)/--alert-border-color: rgba(0, 0, 0, 0.10)/g' $F

# ---------- 7. 滚动条 / 阴影 ----------
sed -i 's/scrollbar-color: rgba(255, 255, 255, 0.25) transparent/scrollbar-color: rgba(0, 0, 0, 0.25) transparent/g' $F
sed -i 's/text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45)/text-shadow: none/g' $F
sed -i 's/box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 2px 10px rgba(0, 0, 0, 0.3)/box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), 0 2px 10px rgba(31, 45, 61, 0.08)/g' $F

# ---------- 8. 青绿主按钮文字恢复白色（modals L556 被 2 误伤） ----------
sed -i '556s/color: #2d3a4a/color: #ffffff/' modals.scss

# ---------- 9. buttons.scss 追加：主按钮白字保障 ----------
cat >> buttons.scss << 'EOF'

/* ===== Light theme patch: primary button keeps white text on teal ===== */
.btn-primary,
.btn-primary:hover,
.btn-primary:focus,
.btn-primary span,
.btn-primary div,
.btn-primary .oi {
    color: #ffffff !important;
}
EOF

chown -R odoo20:odoo20 /opt/odoo20/addons/theme_liquid_glass/static/src/scss/
echo LIGHT_SED_OK
