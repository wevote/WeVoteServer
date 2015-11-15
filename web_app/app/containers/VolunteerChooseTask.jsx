import React from "react";
import axios from 'axios';
import MainMenu from "components/base/MainMenu";
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
                <MainMenu />
                <div className="container-fluid well well-90">
					<h4 className="text-left">Choose a Volunteer Task</h4>
                    <ul className="list-group">
                        <li className="list-group-item"><Link to="volunteer">Find Voter Guides</Link> (2 minutes)</li>
                        <li className="list-group-item"><Link to="volunteer">Verify Voter Guides</Link> (2 minutes)</li>
                        <li className="list-group-item"><Link to="volunteer">Enter Voter Guides</Link> (5-10 minutes)</li>
                    </ul>
                </div>
			</div>
		);
	}
}
