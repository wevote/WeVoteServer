import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import { Link } from "react-router";
import React from "react";

export default class MoreChangeLocationPage extends React.Component {
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
					<h2 className="text-center">Change Location</h2>
					<div>
						<label htmlFor="address">My Ballot Location</label><br />
						<span className="small">Please enter the address (or just the city) where you registered to
						vote. The more location information you can provide, the more ballot information will
						be visible.</span>
						<input type="text" name="address" className="form-control" />
					</div>
				</div>
			</div>
		);
	}
}
