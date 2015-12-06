import axios from 'axios';
import BottomContinueNavigation from "components/navigation/BottomContinueNavigation";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Alert, Button, ButtonToolbar, Input, ProgressBar } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesVoterAddTwitterPage extends React.Component {
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
    <HeaderBackNavigation header_text={"Create Voter Guide"} back_to_text={"< Back"} link_route={'guides_voter_add_existing_link'} />
	<div className="container-fluid well well-90">
        <h4>Help Your Twitter Followers Find Voter Guide</h4>
        <ProgressBar striped bsStyle="success" now={40} label="%(percent)s% Complete" />

        <div>
            <h5>Method 1</h5>
            <span style={floatRight}>
                <ButtonToolbar>
                    <Link to="guides_voter_choose_election"><Button bsStyle="primary">Sign In With Twitter ></Button></Link>
                </ButtonToolbar>
            </span>
            Sign in with your Twitter account so your followers can find your voter guide.
            Tweets will not be sent on your behalf.
        </div>

        <br />
        <br />
	</div>
    <BottomContinueNavigation link_route_continue={'guides_voter_email'} continue_text={'Continue >'} link_route_cancel={'guides_voter'} cancel_text={"cancel"} />
</div>
		);
	}
}
