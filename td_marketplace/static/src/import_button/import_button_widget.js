/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

class td_WizardImportButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            page: this.props.record.data.page,
            per_page: this.props.record.data.per_page,
            do_update:  this.props.record.data.do_update,
        });

        this.props.record.update({ page: this.state.page, per_page: this.state.per_page}, { save: true })

        this.dialog = useService("dialog");
        this.actionService = useService("action");  

    }

    async onClick() {

        let result = true;

        while (result === true) {

            result = await this.orm.call(this.props.record.resModel, this.props.method, [
                this.props.record.resId,
                this.props.record.data.page,
                this.props.record.data.per_page,
                this.props.record.data.do_update,
            ]);
    
            if (result === true) {
                this.state.page += 1;
                await this.props.record.update({ page: this.state.page }, { save: true });
            }
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
td_WizardImportButton.template = "td_marketplace.WizardImportButton";

export const c_td_WizardImportButton = {
    component: td_WizardImportButton,
    extractProps: ({ attrs }) => {
        return {
            method: attrs.button_name,
            title: attrs.title,
        };
    },
};
registry.category("view_widgets").add("td_wizard_import_button", c_td_WizardImportButton);
