import axios from 'axios';
import BottomContinueNavigation from "components/navigation/BottomContinueNavigation";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar, Input, ProgressBar } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesVoterEmailVerifyPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
    <HeaderBackNavigation header_text={"Create Voter Guide"} back_to_text={"< Back"} link_route={'guides_voter_email'} />
	<div className="container-fluid well well-90">
        <h4>Verification Email Sent</h4>
        <ProgressBar striped bsStyle="success" now={70} label="%(percent)s% Complete" />
		<div>
			<p>Thank you, an email has been sent to 'email@email.com' with the subject 'Please verify your email address'.</p>
			<br />
			<br />
			<br />
		</div>
	</div>
    <BottomContinueNavigation link_route_continue={'guides_voter_choose_election'} continue_text={'Continue >'} link_route_cancel={'guides_voter'} cancel_text={"cancel"} />
</div>
		);
	}
}
