import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class AddFriendsConfirmedPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<HeaderBackNavigation back_to_text={"< Back to My Ballot"} />
	<div className="container-fluid well well-90">
		<h2 className="text-center">Add Friends</h2>
		<div>
			<span>Your email has been sent.</span><br />
			<br />
			<br />
			<br />
			<Link to="ballot"><Button bsStyle="primary">Return to My Ballot</Button></Link>
		</div>
	</div>
</div>
		);
	}
}
