import axios from 'axios';
import BallotReturnNavigation from "../../components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class AddFriendsFromAddressPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
                <BallotReturnNavigation back_to_ballot={false} />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Add Friends</h2>
					<div>
						<label htmlFor="last-name">Please enter 'From' email address.</label><br />
						<Input type="text" addonBefore="@" name="add_friends_message" className="form-control"
                               placeholder="Enter your email address" />
						This is the email where your friends can reply to you. We will never sell your email address.
						See <Link to="ballot">privacy policy</Link>.
						<br />
						<Link to="add_friends_confirmed">
							<Button bsStyle="primary">Send</Button>
						</Link><br />
                        <br />
                        <br />
                        <br />
                        OR<br />
						<Link to="add_friends_confirmed">
							<Button bsStyle="primary">Sign in with Facebook</Button>
						</Link><br />
					</div>
				</div>
			</div>
		);
	}
}
