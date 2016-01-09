import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class AddFriendsMessagePage extends React.Component {
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
	<HeaderBackNavigation />
	<div className="container-fluid well well-90">
		<h2 className="text-center">Add Friends</h2>
		<div>
			<label htmlFor="last-name">Would you like to include a message? <span>(Optional)</span></label><br />
			<input type="text" name="add_friends_message" className="form-control"
				   defaultValue="Please join me in preparing for the upcoming election." /><br />
			<br />
			<span  style={floatRight}>
				<Link to="add_friends_from_address"><Button bsStyle="primary">Next ></Button></Link>
			</span>
		</div>
	</div>
</div>
		);
	}
}
