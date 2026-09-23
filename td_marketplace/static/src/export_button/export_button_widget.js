/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

class td_WizardExportButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            comment: 'Ready to export',
        });

        this.props.record.update({ comment: this.state.comment}, { save: true })

        this.dialog = useService("dialog");
        this.actionService = useService("action");  

    }

    async onClick() {

        let result = true;
        let page = 0;

        while (result === true) {
           page += 1;
           this.state.cooment = 'Export package: ' + page
           await this.props.record.update({ comment: this.state.cooment }, { save: true });

           result = await this.orm.call(this.props.record.resModel, this.props.method, [
                this.props.record.resId,
           ]);
        }
    
        this.showDialog();

    }

    showDialog() {

        this.dialog.add(
                AlertDialog,
                {
                    title: "Operation completed",
                    body: "The operation was conpleted",
                },
                {
                    onClose: () => this.closeWidget(),
                }
            );

    }

    closeWidget() {
        this.actionService.doAction({
            type: 'ir.actions.act_window_close'
        });        
    }
}
td_WizardExportButton.template = "td_marketplace.WizardExportButton";

export const c_td_WizardExportButton = {
    component: td_WizardExportButton,
    extractProps: ({ attrs }) => {
        return {
            method: attrs.button_name,
            title: attrs.title,
        };
    },
};
registry.category("view_widgets").add("td_wizard_export_button", c_td_WizardExportButton);
