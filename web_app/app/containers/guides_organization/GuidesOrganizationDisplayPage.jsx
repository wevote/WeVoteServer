import AskOrShareAction from "components/base/AskOrShareAction";
import axios from 'axios';
import CopyLinkNavigation from "../../components/base/CopyLinkNavigation";
import ListTitleNavigation from "../../components/base/ListTitleNavigation";
import MoreInfoIconAction from "../../components/base/MoreInfoIconAction";
import React from "react";
import { Button, ButtonToolbar, Input, Navbar } from "react-bootstrap";
import { Link } from "react-router";

export default class GuidesOrganizationDisplayPagePage extends React.Component {
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
    <ListTitleNavigation header_text={""} back_to_on={true} back_to_text={"< Back"} link_route={'guides_voter'} />
    <div className="container-fluid well well-90">
        <ul className="list-group">
            <li className="list-group-item">
                <h3>
                    <span style={floatRight}><Button bsStyle="info" bsSize="xsmall">Following</Button></span>
                    <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;
                    Organization Name Voter Guide<br />{/* TODO icon-org-placeholder */}
                </h3>
                @OrgName1&nbsp;&nbsp;&nbsp;See Website<br />
                5 of your friends follow Organization Name<br />
                22,452 people follow<br />

                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                <strong>2016 General Election, November 2nd</strong><br />
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur posuere vulputate massa ut efficitur.
                Phasellus rhoncus hendrerit ultricies. Fusce hendrerit vel elit et euismod. Etiam bibendum ultricies
                viverra. Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
                Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)<br />
                <AskOrShareAction link_text={"Share Organization"} />
                <br />
            </li>
        </ul>
        <ul className="list-group">
            <li className="list-group-item">
                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
                <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
                <span>supports</span> Fictional Candidate<br />
                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                Running for US House - District 12&nbsp;<br />
                  Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
                  Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)
                <br />
            </li>
        </ul>
        <ul className="list-group">
            <li className="list-group-item">
                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
                <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
                <span>supports</span> Politician Name<br />
                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                Running for Governor<br />
            </li>
        </ul>
        <ul className="list-group">
            <li className="list-group-item">
                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
                <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
                <span>opposes</span> Another Candidate<br />
                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                Running for Judge<br />
            </li>
        </ul>
    </div>
	<CopyLinkNavigation button_text={"Copy Link to Voter Guide"} />
</div>
		);
	}
}
