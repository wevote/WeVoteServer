"use strict";

import FollowOrIgnoreAction from "components/base/FollowOrIgnoreAction";
import linksCSS from "assets/css/links.css";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";
import styles from "containers/ballot/BallotHomePage.css";
import linkCSS from "assets/css/links.css";

export default class OrganizationsToFollowList extends React.Component {
	render() {
		return (
<div>
		<div className="row">
				<div className="pull-left col-xs-1 col-md-4">
					<Link className={linkCSS.linkLight} to="org_endorsements" params={{org_id: 27}}>
						<i className={styles.iconSmall + " icon-icon-org-placeholder-6-2 icon-light"}></i>{/* TODO icon-org-placeholder */}
					</Link>
        </div>
        <FollowOrIgnoreAction />
        <div className="pull-right col-xs-7 col-md-8">
          <div className={styles.bufferNone}>
            <Link to="org_endorsements" params={{id: 2, org_id: 27}} className={linksCSS.linkLight}>
              Organization Name
            </Link>
          </div>
					<span className="small">
						@OrgName1 (<Link to="org_endorsements" params={{id: 2, org_id: 27}}>read more</Link>)
					</span>
			</div>
		</div>
		<div className="row">
				<div className="pull-left col-xs-1 col-md-4">
					<Link className={linkCSS.linkLight} to="org_endorsements" params={{org_id: 27}}>
						<i className={styles.iconSmall + " icon-icon-org-placeholder-6-2 icon-light"}></i>{/* TODO icon-org-placeholder */}
					</Link>
        </div>
        <FollowOrIgnoreAction />
        <div className="pull-right col-xs-7 col-md-8">
          <div className={styles.bufferNone}>
            <Link to="org_endorsements" params={{id: 2, org_id: 27}} className={linksCSS.linkLight}>
              Another Organization Name
            </Link>
          </div>
					<span className="small">
						@OrgName2 (<Link to="org_endorsements" params={{id: 2, org_id: 27}}>read more</Link>)
					</span>
        </div>
		</div>
</div>
        );
	}
}
