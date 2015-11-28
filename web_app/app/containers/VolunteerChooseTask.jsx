import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class VolunteerChooseTask extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
                <HeaderBackNavigation />
                <div className="container-fluid well well-90">
					<h4 className="text-left">Choose a Volunteer Task</h4>
                    <ul className="list-group">
                        <li className="list-group-item">Find Voter Guides (2 minutes) <Link to="volunteer"><Button bsStyle="primary" bsSize="small">Start ></Button></Link></li>
                        <li className="list-group-item">Verify Voter Guides (2 minutes) <Link to="volunteer"><Button bsStyle="primary" bsSize="small">Start ></Button></Link></li>
                        <li className="list-group-item">Enter Voter Guides (5-10 minutes) <Link to="volunteer"><Button bsStyle="primary" bsSize="small">Start ></Button></Link></li>
                    </ul>
                </div>
			</div>
		);
	}
}
