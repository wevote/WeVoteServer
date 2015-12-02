import axios from 'axios';
import ListTitleNavigation from "components/base/ListTitleNavigation";
import React from "react";
import { Alert, Button, ButtonToolbar, Input, ProgressBar } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesOwnershipConfirmedPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
        var floatRight = {
            float: 'right'
        };
	    return (
<div>
    <ListTitleNavigation header_text={"Create Voter Guide"} back_to_on={true} back_to_text={"< Back"} link_route={'guides_organization_add_results'} />
	<div className="container-fluid well well-90">
        <h4>Your Authority is Confirmed</h4>
        <ProgressBar striped bsStyle="success" now={100} label="%(percent)s% Complete" />

        <div>
            <span style={floatRight}>
                <ButtonToolbar>
                    <Link to="guides_organization_edit" params={{guide_id: 27}}><Button bsStyle="primary">Edit Voter Guide ></Button></Link>
                </ButtonToolbar>
            </span>
            Go to the interface where you can edit this voter guide.
        </div>
        <br />
        <br />
	</div>
</div>
		);
	}
}
