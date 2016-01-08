import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import BottomContinueNavigation from "components/navigation/BottomContinueNavigation";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";
import UnfollowAction from "components/base/UnfollowAction";

{/* VISUAL DESIGN HERE:  */}

export default class DonatePage extends React.Component {
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
		<h2 className="text-center">Donate</h2>

        Coming soon.
    </div>
</div>
		);
	}
}
