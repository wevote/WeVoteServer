"use strict";

import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import BottomContinueNavigation from "components/base/BottomContinueNavigation";
import ListTitleNavigation from "components/base/ListTitleNavigation";
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
<div>
    <ListTitleNavigation header_text={"Here's the idea - Learn from Community"} back_to_on={false} />

    <ul className="list-group">
        <li className="list-group-item">You have organizations and friends you trust when it comes time to
          vote. Follow them so you can see what they endorse on your ballot.<br />
          <br />
        Or skip this.
            <span style={floatRight}><Link to="intro_contests">
                <Button bsStyle="primary">Start on My Own ></Button>
            </Link></span>
            <br />
            <br />
        </li>
        <li className="list-group-item">
            <label htmlFor="search_opinions">Follow Like-Minded Organizations</label><br />
            <input type="text" name="search_opinions" className="form-control"
               placeholder="Search by name or twitter handle." /><br />

            <OrganizationsToFollowList />
        </li>
    </ul>
    <BottomContinueNavigation link_route_continue={'intro_contests'} />

</div>
		);
	}
}
