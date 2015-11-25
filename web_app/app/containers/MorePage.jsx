import React from "react";
import axios from 'axios';
import MainMenu from "components/base/MainMenu";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import { Link } from "react-router";

export default class MorePage extends React.Component {
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
        <h4 className="text-left">My Ballot</h4>
        <ul className="list-group">
            <li className="list-group-item">Print, Save or Email Ballot</li>
            <li className="list-group-item"><Link to="ask_or_share">Share with Friends</Link></li>
            <li className="list-group-item"><Link to="guides_voter">My Voter Guides</Link></li>
            <li className="list-group-item"><Link to="more_change_location">My Ballot Location</Link></li>
            <li className="list-group-item">Public Opinions I Follow</li>
        </ul>
        <h4 className="text-left">My Profile Settings</h4>
        <ul className="list-group">
            <li className="list-group-item">My Friends</li>
            <li className="list-group-item">Account Settings</li>
            <li className="list-group-item">Terms and Policies</li>
        </ul>
        <h4 className="text-left">About</h4>
        <ul className="list-group">
            <li className="list-group-item">About We Vote</li>
            <li className="list-group-item">Donate</li>
            <li className="list-group-item"><Link to="volunteer">Volunteer</Link></li>
            <li className="list-group-item">Admin</li>
        </ul>
    </div>
    <BallotMajorNavigation />
</div>
		);
	}
}
