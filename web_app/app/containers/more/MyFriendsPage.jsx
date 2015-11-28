import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import FriendsNavigation from "components/base/FriendsNavigation";
import MainMenu from "components/base/MainMenu";
import React from "react";
import { Link } from "react-router";
import UnfollowAction from "components/base/UnfollowAction";

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
	<HeaderBackNavigation link_route={'more'} />
	<FriendsNavigation />
	<div className="container-fluid well well-90">
		<h4 className="text-left">My Friends</h4>
		<ul className="list-group">
			<li className="list-group-item">
				<UnfollowAction action_text={"Unfriend"} />
				<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
				Janet Smith</li>
			<li className="list-group-item">
				<UnfollowAction action_text={"Unfriend"} />
				<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
				Will Rogers</li>
			<li className="list-group-item">
				<UnfollowAction action_text={"Unfriend"} />
				<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
				Andrea Moed</li>
			<li className="list-group-item">
				<UnfollowAction action_text={"Unfriend"} />
				<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
				Amy Muller</li>
		</ul>
	</div>
</div>
		);
	}
}
