import React from "react";
import axios from 'axios';
import MainMenu from "components/base/MainMenu";
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
                <MainMenu />
                <div className="container-fluid well well-90">
					<h4 className="text-left">Volunteer With We Vote</h4>
                    <p>Do you have 2 minutes right now?<br />
                        Click the button and make a difference. Join the volunteer movement that is making it
                        easier for all of us to vote!
                    </p>

                    <Link to="volunteer">Help Now ></Link><br />
                        <br />
                    <p>Do you have a favorite volunteer task?</p>

                    <Link to="volunteer_choose_task">Find Task Now ></Link><br />
                        <br />
                </div>
			</div>
		);
	}
}
