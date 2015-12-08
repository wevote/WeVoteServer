import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import BottomContinueNavigation from "components/navigation/BottomContinueNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class AddFriends extends React.Component {
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
	<HeaderBackNavigation back_to_text={"< Back to My Ballot"} />
	<div className="container-fluid well well-90">
		<h2 className="text-center">Add Friends</h2>
		<div>
			<label htmlFor="last-name">Include a Message <span className="small">(Optional)</span></label><br />
			<input type="text" name="add_friends_message" className="form-control"
				   defaultValue="Please join me in preparing for the upcoming election." /><br />
			<Input type="text" addonBefore="@" name="email_address" className="form-control"
				   placeholder="Enter email address(es) of friend(s) here" />
			<span>These friends will see what you support, oppose, and which opinions you follow.
				We never sell email addresses.</span><br />
		</div>
	</div>
    <BottomContinueNavigation link_route_continue={'add_friends_from_address'} continue_text={'Next >'} />
</div>
		);
	}
}
