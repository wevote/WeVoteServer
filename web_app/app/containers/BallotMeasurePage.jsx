import axios from 'axios';
import BallotItemNavigation from "components/base/BallotItemNavigation";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import { Link } from "react-router";
import React from "react";

export default class BallotMeasurePage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<BallotItemNavigation back_to_ballot={true} is_measure={true} />
	<div className="container-fluid well well-90">
		<h2 className="text-center">Measure AA</h2>
		<ul className="list-group">
		  <li className="list-group-item">
			  <Link to="ballot_measure_one_position" params={{id: 2, org_id: 7}}>
				<span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Organization Name<br />{/* TODO icon-org-placeholder */}
				supports
			  </Link>
		  </li>
		  <li className="list-group-item">
              <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Another Organization<br />{/* TODO icon-org-placeholder */}
		        opposes
          </li>
		</ul>
	</div>
	<BallotMajorNavigation />
</div>
		);
	}
}
