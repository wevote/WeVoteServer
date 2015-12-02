import React from "react";

import { Link } from "react-router";

// components
import BallotReturnNavigation from "components/base/BallotReturnNavigation.jsx";
import BottomContinueNavigation from "components/base/BottomContinueNavigation.jsx";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList.jsx";
import UnfollowAction from "components/base/UnfollowAction.jsx";


{/* VISUAL DESIGN HERE:  */}

export default class About extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<BallotReturnNavigation back_to_ballot={false} link_route={'more'} />
	<div className="container-fluid well well-90">
		<h2 className="text-center">About We Vote</h2>

        <ul className="list-group">
          <li className="list-group-item">
            <UnfollowAction />
            <Link to="org_endorsements" params={{org_id: 27}}>
                <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Organization Name<br />{/* TODO icon-org-placeholder */}
                    <span className="small">
                        @OrgName1 (read more)
                    </span>
            </Link>
          </li>
          <li className="list-group-item">
            <UnfollowAction />
              <Link to="org_endorsements" params={{org_id: 27}}>
                <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Another Organization<br />{/* TODO icon-org-placeholder */}
                    <span className="small">
                        @OrgName2 (read more)
                    </span>
              </Link>
          </li>
        </ul>
    </div>
</div>
		);
	}
}
