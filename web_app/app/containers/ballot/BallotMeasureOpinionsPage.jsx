import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";
import InfoIconAction from "components/base/InfoIconAction";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import { Link } from "react-router";
import React from "react";
import StarAction from "components/base/StarAction";

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
    <HeaderBackNavigation />
    <div className="container-fluid well well-90">
        <h2 className="text-center">More Opinions I Can Follow</h2>

        <ul className="list-group">
            <li className="list-group-item">
                <StarAction we_vote_id={'wvcand001'} />
				Measure AA
                <InfoIconAction we_vote_id={'wvcand001'} />
			</li>
        </ul>
		<OrganizationsToFollowList />
    </div>
</div>
);
	}
}
