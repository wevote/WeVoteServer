import axios from 'axios';
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

{/* VISUAL DESIGN HERE: https://invis.io/E45246B2C */}

export default class ConnectPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
        var floatRight = {
            float: 'right'
        };
	    return (
<div>
	<div className="container-fluid well well-90">
		<h4 className="text-left">Add Friends</h4>
        <p>Friends can see what you support and oppose.</p>
        <Input type="text" addonBefore="@" name="email_address" className="form-control"
               placeholder="Enter email address(es) of friend(s) here" />
        <span style={floatRight}>
            <Link to="add_friends"><Button bsStyle="primary">Next &gt;</Button></Link>
        </span>
        <span className="small">Separate email addresses with commas. We never sell emails.</span>
        <br />
        <br />

		<h4 className="text-left">Follow More Opinions</h4>
		<input type="text" name="search_opinions" className="form-control"
			   placeholder="Search by name or twitter handle." />
        <Link to="add_friends_message"><Button bsStyle="primary">Select from those I Follow on Twitter &gt;</Button></Link>
		<OrganizationsToFollowList />

		<h4 className="text-left">Create Voter Guide</h4>
        <p>To share your opinions publicly, create a voter guide.</p>
        <Link to="guides_voter"><Button bsStyle="primary">Create Public Voter Guide &gt;</Button></Link>
        <br />
        <br />
	</div>
    <BallotMajorNavigation />
</div>
		);
	}
}
