import AskOrShareAction from "components/base/AskOrShareAction";
import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar, DropdownButton, MenuItem } from "react-bootstrap";
import { Link } from "react-router";

export default class OrgEndorsementsPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
    <BallotReturnNavigation back_to_ballot={false} />
    <div className="container-fluid well well-90">
        <ul className="list-group">
            <li className="list-group-item">
                <span className="icon_organization"></span>&nbsp;Organization Name <span><Button bsStyle="info" bsSize="xsmall">Follow</Button></span><br />
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
              <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
              <span className="icon_candidate"></span>&nbsp;<span>supports</span> Fictional Candidate<br />
              for US House - District 12&nbsp;<br />
                  Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
                  Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)
              <br />
          </li>
        </ul>
        <ul className="list-group">
          <li className="list-group-item">
              <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
              <span className="icon_candidate"></span>&nbsp;<span>supports</span> Politician Name<br />
              for Governor<br />
          </li>
        </ul>
        <ul className="list-group">
          <li className="list-group-item">
              <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}></Link>{/* Implement later */}
              <span className="icon_candidate"></span>&nbsp;<span>opposes</span> Another Candidate<br />
              for Judge<br />
          </li>
        </ul>
    </div>
</div>
		);
	}
}
