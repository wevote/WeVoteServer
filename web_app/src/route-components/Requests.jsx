import React from "react";

import MainMenu from "components/base/MainMenu";
import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";

export default class Requests extends React.Component {
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
			</div>
		);
	}
}
