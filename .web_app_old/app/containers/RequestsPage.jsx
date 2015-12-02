import axios from 'axios';
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";
import MainMenu from "components/base/MainMenu";
import React from "react";
import { Link } from "react-router";

export default class RequestsPage extends React.Component {
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
					<h4 className="text-left">Friend Requests</h4>
                    <ul className="list-group">
                        <li className="list-group-item">
		                    <FollowOrIgnoreAction action_text={"Add Friend"} />
							<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							Janet Smith</li>
                        <li className="list-group-item">
		                    <FollowOrIgnoreAction action_text={"Add Friend"} />
							<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							Will Rogers</li>
                        <li className="list-group-item">
		                    <FollowOrIgnoreAction action_text={"Add Friend"} />
							<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							Andrea Moed</li>
                        <li className="list-group-item">
		                    <FollowOrIgnoreAction action_text={"Add Friend"} />
							<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							Amy Muller</li>
                    </ul>
                </div>
                <BallotMajorNavigation />
			</div>
		);
	}
}
