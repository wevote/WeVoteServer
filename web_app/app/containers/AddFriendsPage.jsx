import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
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
						<input type="text" name="email_address" className="form-control" defaultValue="Enter email address of friend here" /><br />
						<span>+ Add more email addresses</span><br />
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
