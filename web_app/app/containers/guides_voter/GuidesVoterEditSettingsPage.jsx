import axios from 'axios';
import CopyLinkNavigation from "components/navigation/CopyLinkNavigation";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Alert, Button, ButtonToolbar, Input, Navbar, ProgressBar } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesVoterEditSettingsPage extends React.Component {
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
    <HeaderBackNavigation header_text={"Edit Voter Guide Settings"} back_to_text={"< Back"} link_route={'guides_voter_edit'} params={{guide_id: 27}} />
	<div className="container-fluid well well-90">
        <h4>My Voter Guide Settings</h4>
        Upload photo&nbsp;&nbsp;&nbsp;
		Remove photo<br />
        <br />
        <h5>Twitter Account(s)</h5>
        Enter twitter account(s) so your followers can find your voter guide.<br />
        <div>
            <span style={floatRight}>
                <Link to="guides_voter_edit_settings" params={{guide_id: 27}}>
                    <Button bsStyle="primary" bsSize="xsmall">remove</Button>
                </Link>
            </span>
            <span>@MyTwitterHandle</span>

            <Input type="text" placeholder="Type in Twitter Handle" />
            <span style={floatRight}>
                <Link to="guides_voter_edit_settings" params={{guide_id: 27}}>
                    <Button bsStyle="primary" bsSize="xsmall">add</Button>{/* TODO I would prefer this be inline with Input */}
                </Link>
            </span>
        </div>
	</div>
	<CopyLinkNavigation button_text={"Copy Link to Voter Guide"} />
</div>
		);
	}
}
