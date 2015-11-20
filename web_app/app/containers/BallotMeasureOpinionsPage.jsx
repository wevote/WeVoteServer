import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import { Link } from "react-router";
import React from "react";

export default class BallotMeasureOpinionsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
                <BallotReturnNavigation />
				<div className="container-fluid well well-90">
					<h2 className="text-center">More Opinions I Can Follow</h2>

					<ul className="list-group">
					  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-info-sign"></span>&nbsp;Measure AA</li>
					  <li className="list-group-item"><span className="icon_organization"></span>&nbsp;<Link to="ballot_measure_one_position" params={{id: 2, org_id: 7}}>Organization Name</Link><br />
					  supports</li>
					  <li className="list-group-item"><span className="icon_organization"></span>&nbsp;Another Organization<br />
					  opposes</li>
					</ul>
				</div>
			</div>
		);
	}
}
