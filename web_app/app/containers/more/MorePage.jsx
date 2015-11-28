import React from "react";
import axios from 'axios';
import LanguageSwitchNavigation from "components/navigation/LanguageSwitchNavigation";
import MainMenu from "../../components/base/MainMenu";
import BallotMajorNavigation from "../../components/base/BallotMajorNavigation";
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
    <div className="container-fluid well well-90">
        <LanguageSwitchNavigation />
        <h4 className="text-left">My Ballot</h4>
        <ul className="list-group">
            <li className="list-group-item"><Link to="email_ballot">Print, Save or Email Ballot</Link></li>
            <li className="list-group-item"><Link to="ask_or_share">Share with Friends</Link></li>
            <li className="list-group-item"><Link to="guides_voter">My Voter Guides</Link></li>
            <li className="list-group-item"><Link to="more_change_location">My Ballot Location</Link></li>
            <li className="list-group-item"><Link to="opinions_followed">Public Opinions I Follow</Link></li>
        </ul>
        <h4 className="text-left">My Profile Settings</h4>
        <ul className="list-group">
            <li className="list-group-item"><Link to="my_friends">My Friends</Link></li>
            <li className="list-group-item"><Link to="account_settings">Account Settings</Link></li>
        </ul>
        <h4 className="text-left">About</h4>
        <ul className="list-group">
            <li className="list-group-item"><Link to="about">About We Vote</Link></li>
            <li className="list-group-item"><Link to="donate">Donate</Link></li>
            <li className="list-group-item"><Link to="volunteer">Volunteer</Link></li>
            <li className="list-group-item"><Link to="privacy">Terms and Policies</Link></li>
            <li className="list-group-item"><a href="http://localhost:8000/admin/" target="_blank">Admin</a></li>
        </ul>
    </div>
    <BallotMajorNavigation />
</div>
		);
	}
}
