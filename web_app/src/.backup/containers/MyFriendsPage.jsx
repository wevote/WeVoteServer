import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import FriendsNavigation from "components/base/FriendsNavigation";
import React, { Component } from "react";
import UnfollowAction from "components/base/UnfollowAction";

export default class MyFriends extends Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
            <div>
            	<BallotReturnNavigation back_to_ballot={false} link_route={'more'} />
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
