"use strict";

import FollowOrIgnoreAction from "./FollowOrIgnoreAction.jsx";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class OrganizationsToFollowList extends React.Component {
	render() {
		return (
<span>
	<ul className="list-group">
	  <li className="list-group-item">
		<FollowOrIgnoreAction />
		<Link to="org_endorsements" params={{org_id: 27}}>
			<span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Organization Name<br />{/* TODO icon-org-placeholder */}
				<span className="small">
					@OrgName1 (read more)
				</span>
		</Link>
	  </li>
	  <li className="list-group-item">
		<FollowOrIgnoreAction />
		  <Link to="org_endorsements" params={{org_id: 27}}>
			<span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Another Organization<br />{/* TODO icon-org-placeholder */}
			  	<span className="small">
					@OrgName2 (read more)
				</span>
		  </Link>
	  </li>
	</ul>
</span>
        );
	}
}
