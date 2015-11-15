import React from "react";
import { Link } from "react-router";

export default class BallotFeedNavigation extends React.Component {
	render() {
		return <div className="row">
            <nav className="navbar navbar-main navbar-fixed-top">
                <div className="container-fluid">
                    <div className="left-inner-addon">
					<h2 className="text-left">My Ballot</h2>
                    <p className="text-right">
                        <Link to="more_change_location">Change Location</Link>&nbsp;&nbsp;&nbsp;
                        <Link to="ballot_add_friends">Add Friends</Link>&nbsp;&nbsp;&nbsp;
                        <Link to="ballot_opinions">More Opinions</Link></p>
                    </div>
                </div>
            </nav>
		</div>;
	}
}
