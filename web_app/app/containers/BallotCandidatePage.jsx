import axios from 'axios';
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import { Link } from "react-router";
import MainMenu from "components/base/MainMenu";
import React from "react";

export default class BallotCandidatePage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
                <MainMenu />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Fictional Candidate</h2>
                    <p><Link to="ballot_candidate_opinions">More Opinions</Link></p>

					<ul className="list-group">
					  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-info-sign"></span>&nbsp;Running for US House - District 12</li>
					  <li className="list-group-item"><span className="icon_organization"></span>&nbsp;<Link to="ballot_candidate_one_position">Organization Name</Link><br />
					  supports</li>
					  <li className="list-group-item"><span className="icon_organization"></span>&nbsp;Another Organization<br />
					  opposes</li>
					</ul>
				</div>
                <BallotMajorNavigation />
			</div>
		);
	}
}
