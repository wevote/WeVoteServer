import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class AddFriendsPage extends React.Component {
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
                <BallotReturnNavigation back_to_ballot={true} />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Add Friends</h2>
					<div>
						<label htmlFor="last-name">Include a Message <span className="small">(Optional)</span></label><br />
						<input type="text" name="add_friends_message" className="form-control"
							   defaultValue="Please join me in preparing for the upcoming election." /><br />
						<Input type="text" addonBefore="@" name="email_address" className="form-control"
                               placeholder="Enter email address(es) of friend(s) here" />
						<span>Separate email addresses with commas. We never sell email addresses.</span><br />
						<br />
						<br />
						<br />
						<br />
						These friends will see what you support, oppose, and which opinions you follow.<br />
						<span  style={floatRight}>
							<Link to="add_friends_from_address"><Button bsStyle="primary">Next ></Button></Link>
						</span>
					</div>
				</div>
			</div>
		);
	}
}
