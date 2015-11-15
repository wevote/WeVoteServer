import axios from 'axios';
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import { Link } from "react-router";
import MainMenu from "components/base/MainMenu";
import React from "react";

export default class BallotHomePage extends React.Component {
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
					<h2 className="text-center">My Ballot</h2>
                    <p><Link to="ballot_opinions">More Opinions</Link></p>

					<ul className="list-group">
					  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-info-sign"></span>&nbsp;US House - District 12</li>
					  <li className="list-group-item"><span className="icon_person"></span>&nbsp;<Link to="ballot_candidate">Fictional Candidate</Link></li>
					  <li className="list-group-item"><span className="icon_person"></span>&nbsp;Another Candidate</li>
					</ul>

					<ul className="list-group">
					  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-info-sign"></span>&nbsp;<Link to="ballot_measure">Measure AA</Link></li>
					</ul>
				</div>
                <BallotMajorNavigation />
			</div>
		);
	}
}
