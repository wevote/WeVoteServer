import axios from 'axios';
import BallotItemNavigation from "components/base/BallotItemNavigation";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import { Link } from "react-router";
import React from "react";

export default class BallotCandidateOnePositionPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
			<div>
                <BallotItemNavigation back_to_ballot={false} is_measure={false} />
				<div className="container-fluid well well-90">
					<h2 className="text-center">Fictional Candidate</h2>

					<ul className="list-group">
					  <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-info-sign"></span>&nbsp;Running for US House - District 12</li>
					  <li className="list-group-item"><span className="icon_organization"></span>&nbsp;Organization Name<br />
					  supports</li>
					  <li className="list-group-item">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis tempor vel mauris non convallis. Etiam vulputate libero vitae enim pretium, et lobortis nulla ultrices. Quisque at mi finibus, ullamcorper nulla et, bibendum nisl. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Ut suscipit sed justo eget molestie. Suspendisse molestie justo tristique vulputate posuere. Donec efficitur nunc vitae arcu aliquam, eget dignissim est fermentum. Mauris interdum dolor lacus, euismod convallis dui molestie id.</li>
					</ul>
				</div>
                <BallotMajorNavigation />
			</div>
		);
	}
}
