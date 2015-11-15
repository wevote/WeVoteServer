import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import { Link } from "react-router";
import React from "react";

export default class BallotAddFriendsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
                <BallotReturnNavigation />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Add Friends</h2>
					<div>
						<label htmlFor="email_addresses">Email Addresses</label><br />
						<input type="text" name="email_addresses" className="form-control" />
					</div>
				</div>
			</div>
		);
	}
}
