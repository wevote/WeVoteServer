import axios from 'axios';
import ElectionsListNavigation from "../../components/base/ElectionsListNavigation";
import ListTitleNavigation from "../../components/base/ListTitleNavigation";
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
    <ListTitleNavigation header_text={"My Voter Guides"} back_to_on={true} back_to_text={"< Back"} />
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
	</div>

	<div className="container-fluid well well-90">
        Current Voter Guides
        <ElectionsListNavigation link_route={'guides_organization_display'} link_route_edit={'guides_organization_edit'} params={{guide_id: 27}} />
    </div>

	<div className="container-fluid well well-90">
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
