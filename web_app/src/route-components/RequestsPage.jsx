<<<<<<< HEAD:web_app/src/route-components/RequestsPage.jsx
import React, { Component } from "react";

=======
import axios from 'axios';
import BallotMajorNavigation from "components/navigation/BallotMajorNavigation";
import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";
>>>>>>> master:web_app/app/containers/RequestsPage.jsx
import MainMenu from "components/base/MainMenu";
import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";

export default class RequestsPage extends Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<section>
        <div className="container-fluid well well-90">
					<h4 className="text-left">Friend Requests</h4>
<<<<<<< HEAD:web_app/src/route-components/RequestsPage.jsx
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
=======
              <ul className="list-group">
                <li className="list-group-item">
		              <FollowOrIgnoreAction action_text={"Add Friend"} />
							    <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							         Janet Smith
                </li>
                <li className="list-group-item">
		              <FollowOrIgnoreAction action_text={"Add Friend"} />
							    <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							          Will Rogers
                </li>
                <li className="list-group-item">
		              <FollowOrIgnoreAction action_text={"Add Friend"} />
							    <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							           Andrea Moed
                </li>
                <li className="list-group-item">
		              <FollowOrIgnoreAction action_text={"Add Friend"} />
							    <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
							           Amy Muller
                </li>
              </ul>
        </div>
        <BallotMajorNavigation />
			</section>
>>>>>>> master:web_app/app/containers/RequestsPage.jsx
		);
	}
}
