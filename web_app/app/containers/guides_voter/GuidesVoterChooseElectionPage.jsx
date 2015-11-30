import axios from 'axios';
import BottomContinueNavigation from "components/navigation/BottomContinueNavigation";
import ElectionsListNavigation from "components/base/ElectionsListNavigation";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar, Input, ProgressBar } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesVoterChooseElectionPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
    <HeaderBackNavigation header_text={"Create Voter Guide"} back_to_text={"< Back"} link_route={'guides_voter_email'} />
	<div className="container-fluid well well-90">
        <h4>Choose Election</h4>
        <ProgressBar striped bsStyle="success" now={80} label="%(percent)s% Complete" />
		<p>Which election are you creating a voter guide for?</p>
		<form>
        <ElectionsListNavigation link_route={'guides_voter_edit'} />
		</form>
	</div>
    <BottomContinueNavigation link_route_continue={'guides_voter_edit'} params={{guide_id: 27, complete: true}} continue_text={'Continue >'} link_route_cancel={'guides_voter'} cancel_text={"cancel"} />
</div>
		);
	}
}
