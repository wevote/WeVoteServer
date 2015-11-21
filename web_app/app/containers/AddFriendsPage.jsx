import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class AddFriendsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
                <BallotReturnNavigation back_to_ballot={true} />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Add Friends</h2>
					<div>
						<Input type="text" addonBefore="@" name="email_address" className="form-control" defaultValue="Enter email address(es) of friend(s) here" />
						<span>Separate email addresses with commas. We never sell email addresses.</span><br />
						<br />
						<br />
						<br />
						<br />
						These friends will see what you support, oppose, and which opinions you follow.<br />
						<Link to="add_friends_message"><Button bsStyle="primary">Next ></Button></Link>
					</div>
				</div>
			</div>
		);
	}
}
