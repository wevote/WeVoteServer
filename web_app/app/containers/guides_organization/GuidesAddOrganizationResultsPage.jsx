import axios from 'axios';
import BottomContinueNavigation from "../../components/base/BottomContinueNavigation";
import ListTitleNavigation from "../../components/base/ListTitleNavigation";
import React from "react";
import { Alert, Button, ButtonToolbar, Input, ProgressBar } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesAddOrganizationResultsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
        var floatRight = {
            float: 'right'
        };
	    return (
<div>
    <ListTitleNavigation header_text={"Create Voter Guide"} back_to_on={true} back_to_text={"< Back"} link_route={'guides_organization_add_search'} />
	<div className="container-fluid well well-90">
        <h4>Existing Organizations Found</h4>
        <ProgressBar striped bsStyle="success" now={60} label="%(percent)s% Complete" />
		<div>
			<Alert bsStyle="success">
				We found these organizations. Is one of them the organization you are adding? If not, click the 'Create New Voter Guide' button.
			</Alert>

            <span>
                <ul className="list-group">
                  <li className="list-group-item">
                    <Link to="org_endorsements" params={{org_id: 27}}>
                        <span style={floatRight}>
                            <ButtonToolbar>
                                <Button bsStyle="info">Choose</Button>
                            </ButtonToolbar>
                        </span>
                        <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Organization Name<br />{/* TODO icon-org-placeholder */}
                            <span className="small">
                                @OrgName1<br />
                                http://www.SomeOrg.org
                            </span>
                    </Link>
                  </li>
                  <li className="list-group-item">
                      <Link to="org_endorsements" params={{org_id: 27}}>
                        <span style={floatRight}>
                            <ButtonToolbar>
                                <Button bsStyle="info">Choose</Button>
                            </ButtonToolbar>
                        </span>
                        <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Another Organization<br />{/* TODO icon-org-placeholder */}
                            <span className="small">
                                @OrgName2<br />
                                http://www.SomeOrg.org
                            </span>
                      </Link>
                  </li>
                </ul>
            </span>
			<br />
			<br />
			<br />
		</div>
	</div>
    <BottomContinueNavigation link_route_continue={'guides_organization_add'} continue_text={'Create New Voter Guide'} link_route_cancel={'guides_voter'} cancel_text={"cancel"} />
</div>
		);
	}
}
