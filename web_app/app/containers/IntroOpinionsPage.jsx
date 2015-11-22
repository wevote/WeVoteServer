import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import BottomContinueNavigation from "components/base/BottomContinueNavigation";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

{/* VISUAL DESIGN HERE: https://invis.io/TR4A1NYAQ */}

export default class IntroOpinionsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<BallotReturnNavigation back_to_ballot={false} />
	<div className="container-fluid well well-90">
		<h4 className="text-center">Here's the idea - Learn from Community</h4>

		<ul className="list-group">
		  <li className="list-group-item">You have organizations and friends you trust when it comes time to
              vote. Follow them so you can see what they endorse on your ballot.<br />
              <br />
          Or skip this. <Link to="ballot"><Button bsStyle="primary">Start on My Own ></Button></Link>
          </li>
		</ul>

		<input type="text" name="search_opinions" className="form-control"
				   defaultValue="Search by name or twitter handle." /><br />

		<OrganizationsToFollowList />
        <BottomContinueNavigation />
	</div>
</div>
		);
	}
}
