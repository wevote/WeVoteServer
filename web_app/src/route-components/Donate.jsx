import React from "react";

import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import BottomContinueNavigation from "components/base/BottomContinueNavigation";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import UnfollowAction from "components/base/UnfollowAction";

{/* VISUAL DESIGN HERE:  */}

export default class Donate extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
				<BallotReturnNavigation back_to_ballot={false} link_route={'more'} />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Donate</h2>
			        Coming soon.
			    </div>
			</div>
		);
	}
}
