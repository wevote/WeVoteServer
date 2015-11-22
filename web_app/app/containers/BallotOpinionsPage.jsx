import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

{/* VISUAL DESIGN HERE: https://invis.io/TR4A1NYAQ */}

export default class BallotOpinionsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<BallotReturnNavigation back_to_ballot={true} />
	<div className="container-fluid well well-90">
		<h2 className="text-center">More Opinions I Can Follow</h2>
			<input type="text" name="search_opinions" className="form-control"
				   defaultValue="Search by name or twitter handle." /><br />

		<ul className="list-group">
		  <li className="list-group-item">These organizations and public figures have opinions about items on your
              ballot. Click the 'Follow' to pay attention to them.
          </li>
		</ul>

		<ul className="list-group">
		  <li className="list-group-item">
            <Link to="org_endorsements" params={{org_id: 27}}>
                <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Organization Name<br />{/* TODO icon-org-placeholder */}
                @OrgName1<br />
                (read more)
            </Link>
            <span>
                <ButtonToolbar>
                    <Button bsStyle="info">Follow</Button>
                    <Button bsStyle="danger" bsSize="xsmall">Ignore</Button>
                </ButtonToolbar>
            </span>
          </li>
		  <li className="list-group-item">
              <Link to="org_endorsements" params={{org_id: 27}}>
                <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Another Organization<br />{/* TODO icon-org-placeholder */}
                  @OrgName2<br />
                  (read more)
              </Link>
            <span>
                <ButtonToolbar>
                    <Button bsStyle="info">Follow</Button>
                    <Button bsStyle="danger" bsSize="xsmall">Ignore</Button>
                </ButtonToolbar>
            </span>
          </li>
		</ul>
	</div>
</div>
		);
	}
}
