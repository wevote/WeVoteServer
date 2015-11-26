import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";
import InfoIconAction from "components/base/InfoIconAction";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
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
            <li className="list-group-item">
                <InfoIconAction we_vote_id={'wvcand001'} />
				Measure AA
			</li>
        </ul>
		<OrganizationsToFollowList />
    </div>
</div>
);
	}
}
