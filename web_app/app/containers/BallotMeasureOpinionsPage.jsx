import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";
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
            <li className="list-group-item">
              <Link to="org_endorsements" params={{org_id: 3}}><span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Organization Name</Link><br />{/* TODO icon-org-placeholder */}
                supports
                <FollowOrIgnoreAction />
            </li>
            <li className="list-group-item">
                  <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Another Organization<br />{/* TODO icon-org-placeholder */}
                    opposes
                <FollowOrIgnoreAction />
            </li>
        </ul>
    </div>
</div>
);
	}
}
