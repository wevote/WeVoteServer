import axios from 'axios';
import ElectionsListNavigation from "components/base/ElectionsListNavigation";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

{/* VISUAL DESIGN HERE: https://invis.io/RN4071DGB */}

export default class GuidesVoterHomePage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
    <HeaderBackNavigation header_text={"My Voter Guides"} back_to_text={"< Back"} link_route={'more'}  />
	<div className="container-fluid well well-90">
        <h4>Public Sharing</h4>
        <p>Share voting recommendations publicly.<br />
            <span className="small">(For private sharing, see "Add Friends" below.)</span><br />
            <Link to="guides_voter_add_existing_link">
                <Button bsStyle="primary">Create Personal Voter Guide</Button>
            </Link>&nbsp;
            <Link to="guides_organization_add_existing_link">
                <Button bsStyle="primary">Create Voter Guide for Organization</Button>
            </Link>
        </p>

        Current Voter Guides
        <ElectionsListNavigation link_route={'guides_organization_display'} link_route_edit={'guides_voter_edit'} params={{guide_id: 27}} />

        <h4>Private Sharing</h4>
        <p>To share your voting recommendations privately with friends, invite your friends to
            see what you support or oppose.<br />

            <Link to="add_friends">
                <Button bsStyle="primary">Add Friends</Button>
            </Link>
        </p>
    </div>
</div>
		);
	}
}
