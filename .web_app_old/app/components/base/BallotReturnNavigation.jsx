"use strict";

import React from "react";
import { Link } from "react-router";

// This navigation is for simple returns to prior page. Does NOT include other options like "More Opinions".
export default class BallotReturnNavigation extends React.Component {
	render() {
        var link_route;
        if (this.props.link_route) {
            link_route = this.props.link_route;
        } else {
            link_route = 'ballot';
        }
        var back_to_link;
        if (this.props.back_to_ballot) {
            back_to_link = <Link to={link_route}>&lt; Back to My Ballot</Link>;
        } else {
            {/* TODO Add a way to pass in the return url */}
            back_to_link = <Link to={link_route}>&lt; Back</Link>;
        }
		return (
<div className="row">
    <nav className="navbar navbar-main navbar-fixed-top">
        <div className="container-fluid">
            <div className="left-inner-addon">
                {/* Switch between "Back" and "Back to My Ballot" */}
                <p className="text-left">{back_to_link}</p>
            </div>
        </div>
    </nav>
</div>
        );
	}
}
