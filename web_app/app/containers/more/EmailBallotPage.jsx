import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class EmailBallotPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<HeaderBackNavigation link_route={'more'} />
	<div className="container-fluid well well-90">
		<h2 className="text-center">Print, Save or Email Ballot</h2>
		<div>
			<label htmlFor="last-name">Email your ballot to yourself so you can print or save</label><br />
			<Input type="text" addonBefore="@" name="email_address" className="form-control"
				   placeholder="Enter your email address" />
			Email your ballot to yourself so you can print it, or come back
			to it later. We will never sell your email address.
			See <Link to="privacy">privacy policy</Link>.
			<br />
			<Link to="add_friends_confirmed">
				<Button bsStyle="primary">Send</Button>
			</Link><br />
			<br />
			<br />
			OR<br />
			<br />
			<Link to="add_friends_confirmed">
				<Button bsStyle="primary">Sign in with Facebook</Button><br />
				<Button bsStyle="primary">Sign in with Twitter</Button>
			</Link><br />
		</div>
	</div>
</div>
		);
	}
}
