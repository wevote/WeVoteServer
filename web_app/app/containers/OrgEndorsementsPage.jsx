import AskOrShareAction from "components/base/AskOrShareAction";
import axios from 'axios';
import HeaderBackNavigation from "components/navigation/HeaderBackNavigation";
import InfoIconAction from "components/base/InfoIconAction";
import React from "react";
import { Button, ButtonToolbar, DropdownButton, MenuItem } from "react-bootstrap";
import { Link } from "react-router";
import StarAction from "components/base/StarAction";

export default class OrgEndorsementsPage extends React.Component {
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
    <HeaderBackNavigation />
    <div className="container-fluid well well-90">
        <ul className="list-group">
            <li className="list-group-item">
                <span style={floatRight}><Button bsStyle="info" bsSize="xsmall">Follow</Button></span>
                <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
                Organization Name<br />{/* TODO icon-org-placeholder */}
                @OrgName1&nbsp;&nbsp;&nbsp;See Website<br />
                5 of your friends follow Organization Name<br />
                22,452 people follow<br />
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur posuere vulputate massa ut efficitur.
                Phasellus rhoncus hendrerit ultricies. Fusce hendrerit vel elit et euismod. Etiam bibendum ultricies
                viverra. Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
                Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)<br />
                <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-flag"></span> Flag</Link>&nbsp;&nbsp;&nbsp;
                <AskOrShareAction link_text={"Share Organization"} />
                <br />
         </li>
        </ul>
        <ul className="list-group">
          <li className="list-group-item">
              <StarAction we_vote_id={'wvcand001'} />
              <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
              <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
              <span>supports</span> Fictional Candidate
              <InfoIconAction we_vote_id={'wvcand001'} />
              <br />

              <StarAction we_vote_id={'wvcand001'} />
              for US House - District 12
              <InfoIconAction we_vote_id={'wvcand001'} />
              <br />
                  Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
                  Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)
              <br />
          </li>
        </ul>
        <ul className="list-group">
          <li className="list-group-item">
              <StarAction we_vote_id={'wvcand001'} />
              <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
              <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
              <span>supports</span> Politician Name
              <InfoIconAction we_vote_id={'wvcand001'} />
              <br />

              <StarAction we_vote_id={'wvcand001'} />
              for Governor
              <InfoIconAction we_vote_id={'wvcand001'} />
              <br />
          </li>
        </ul>
        <ul className="list-group">
          <li className="list-group-item">
              <StarAction we_vote_id={'wvcand001'} />
              <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
              <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>{/* TODO icon-person-placeholder */}
              <span>opposes</span> Another Candidate
              <InfoIconAction we_vote_id={'wvcand001'} />
              <br />

              <StarAction we_vote_id={'wvcand001'} />
              for Judge
              <InfoIconAction we_vote_id={'wvcand001'} />
              <br />
          </li>
        </ul>
    </div>
</div>
		);
	}
}
