/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, signal } from "@odoo/owl";

export class ShoeDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.data = signal(null);
        this.error = signal(null);
        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        this.error.value = null;
        try {
            this.data.value = await this.orm.silent.call(
                "shoe.dashboard", "get_dashboard_data", []);
        } catch (e) {
            this.error.value = String(e);
        }
    }

    onShortcut(ev) {
        const el = ev.currentTarget;
        if (el.dataset.action === "new_quotation") {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "form"]],
                target: "new",
            });
        } else {
            const aid = Number(el.dataset.aid);
            if (aid) {
                this.action.doAction(aid);
            }
        }
    }

    onOrder(ev) {
        const oid = Number(ev.currentTarget.dataset.oid);
        if (oid) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "sale.order",
                res_id: oid,
                views: [[false, "form"]],
            });
        }
    }

    get chartMax() {
        if (!this.data.value) {
            return 1;
        }
        return Math.max(1, ...this.data.value.months.map((m) => m.value));
    }
}

ShoeDashboard.template = "shoe_theme.Dashboard";

registry.category("actions").add("shoe_theme.dashboard", ShoeDashboard, { force: true });
