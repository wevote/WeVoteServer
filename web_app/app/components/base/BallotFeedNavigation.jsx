//TODO: Break apart the add friends and more opinions list
import React from "react";
import { Link } from "react-router";

export default class BallotFeedNavigation extends React.Component {
	render() {
		return <div className="row">
            <nav className="navbar navbar-main navbar-fixed-top bottom-separator">
                <div className="container-fluid">
                    <div className="left-inner-addon">
                      <h2 className="pull-left no-space bold">My Ballot</h2>
                      <ul className="nav nav-pills pull-right">
                        <li><Link to="more_change_location" className="font-lightest">Oakland, CA (change)</Link></li>
                      </ul>
                    </div>
                </div>
            </nav>
            <div>
              <ul>
                <li><Link to="add_friends">Add Friends</Link></li>
                <li><Link to="ballot_opinions">More Opinions</Link></li>
              </ul>
            </div>
		</div>;
	}
}
