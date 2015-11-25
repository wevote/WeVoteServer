import axios from 'axios';
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

{/* VISUAL DESIGN HERE: TBD */}

export default class ActivityPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<div className="container-fluid well well-90">
		Activity Feed Coming Soon

	</div>
    <BallotMajorNavigation />
</div>
		);
	}
}
