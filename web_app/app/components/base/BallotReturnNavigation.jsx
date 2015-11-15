import React from "react";
import { Link } from "react-router";

// This navigation is for simple returns to prior page. Does NOT include other options like "More Opinions".
export default class BallotReturnNavigation extends React.Component {
	render() {
		return <div className="row">
            <nav className="navbar navbar-main navbar-fixed-top">
                <div className="container-fluid">
                    <div className="left-inner-addon">
                        {/* Create switch between "Back" and "Back to My Ballot" */}
                        <p className="text-left"><Link to="ballot">&lt; Back to My Ballot</Link></p>
                    </div>
                </div>
            </nav>
		</div>;
	}
}
