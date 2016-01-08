"use strict";

import axios from 'axios';
import BottomContinueNavigation from "components/navigation/BottomContinueNavigation";
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

{/* VISUAL DESIGN HERE: https://invis.io/W8439I423 */}

export default class IntroOpinionsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
        var floatRight = {
            float: 'right'
        };
	    return (
<div className="container-fluid">
    <HeaderBackNavigation header_text={"Here's the idea - Learn from Community"} back_to_off={true} />

    <div className="well well-95">
        <p>You have organizations and friends you trust when it comes time to
          vote. Follow them so you can see what they endorse on your ballot.</p>
        <p className="clearfix">Or skip this.
            <span style={floatRight}><Link to="intro_contests">
                <Button bsStyle="primary" bsSize="small">Start on My Own ></Button>
            </Link></span>
        </p>
        <div>
            <label htmlFor="search_opinions">Follow Like-Minded Organizations</label><br />
            <input type="text" name="search_opinions" className="form-control"
               placeholder="Search by name or twitter handle." /><br />

            <OrganizationsToFollowList />
        </div>
    </div>
    <BottomContinueNavigation link_route_continue={'intro_contests'} />

</div>
		);
	}
}
