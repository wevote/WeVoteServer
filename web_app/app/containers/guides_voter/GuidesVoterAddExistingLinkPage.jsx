import axios from 'axios';
import BottomContinueNavigation from "components/navigation/BottomContinueNavigation";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesVoterAddExistingLinkPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
    <HeaderBackNavigation header_text={"Existing Voter Guide?"} back_to_text={"Cancel"} link_route={'guides_voter'} />
	<div className="container-fluid well well-90">
		<div>
            <label htmlFor="existing_link">Do you already publish a voter guide on the web?</label><br />
			<input type="text" name="existing_link" className="form-control"
				   placeholder="Enter the URL of your existing voter guide" /><br />
			<br />
			<br />
			<br />
		</div>
	</div>
    <BottomContinueNavigation link_route_continue={'ballot'} continue_text={'Continue >'} link_route_cancel={'guides_voter'} cancel_text={"cancel"} />
</div>
		);
	}
}
