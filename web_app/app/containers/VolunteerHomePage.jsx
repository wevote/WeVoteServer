import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class VolunteerHomePage extends React.Component {
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
					<h4 className="text-left">Volunteer With We Vote</h4>
                    <p>Do you have 2 minutes right now?<br />
                        Click the button and make a difference. Join the volunteer movement that is making it
                        easier for all of us to vote!
                    </p>

                    <Link to="volunteer"><Button bsStyle="primary">Help Now ></Button></Link><br />
                        <br />
                    <p>Do you have a favorite volunteer task?</p>

                    <Link to="volunteer_choose_task"><Button bsStyle="primary">Find Task Now ></Button></Link><br />
                        <br />
                </div>
			</div>
		);
	}
}
