import AskOrShareAction from "../../components/base/AskOrShareAction";
import axios from 'axios';
import BallotItemNavigation from "../../components/base/BallotItemNavigation";
import BallotMajorNavigation from "../../components/base/BallotMajorNavigation";
import MoreInfoIconAction from "components/base/MoreInfoIconAction";
import React from "react";
import { Button, ButtonToolbar, DropdownButton, MenuItem } from "react-bootstrap";
import { Link } from "react-router";

export default class BallotCandidatePage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
        var support_item;
        if (this.props.support_on) {
            support_item = <Link to="ballot">7 <span className="glyphicon glyphicon-small glyphicon-arrow-up"></span></Link>;
        } else {
            support_item = <Link to="ballot">7 <span className="glyphicon glyphicon-small glyphicon-arrow-up"></span></Link>;
        }

        var oppose_item;
        if (this.props.oppose_on) {
            oppose_item = <Link to="ballot">3 <span className="glyphicon glyphicon-small glyphicon-arrow-down"></span></Link>;
        } else {
            oppose_item = <Link to="ballot">3 <span className="glyphicon glyphicon-small glyphicon-arrow-down"></span></Link>;
        }
	    return (
<div>
    <BallotItemNavigation back_to_ballot={true} is_measure={false} />
    <div className="container-fluid well well-90">
        <ul className="list-group">
            <li className="list-group-item">
                <i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Fictional Candidate{/* TODO icon-person-placeholder */}
                <span className="glyphicon glyphicon-small glyphicon-star-empty"></span>{/* Right align */}
                <br />
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur posuere vulputate massa ut efficitur.
                Phasellus rhoncus hendrerit ultricies. Fusce hendrerit vel elit et euismod. Etiam bibendum ultricies
                viverra. Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
                Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)<br />
                Courtesy of Ballotpedia.org<br />
                <MoreInfoIconAction we_vote_id={'wvcand001'} />
                Running for US House - District 12<br />
                {support_item}&nbsp;&nbsp;&nbsp;
                {oppose_item}&nbsp;&nbsp;&nbsp;
                <AskOrShareAction />
                <br />
 				<div>
					<input type="text" name="address" className="form-control" defaultValue="What do you think?" />
                    <Link to="ballot_candidate" params={{id: 2}}><Button bsSize="small">Post Privately</Button></Link>
				</div>
         </li>
        </ul>
        <ul className="list-group">
          <li className="list-group-item">
              <Link to="ballot_candidate_one_org_position" params={{id: 2, org_id: 27}}>
                  <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Organization Name<br />{/* TODO icon-org-placeholder */}
                  <span>supports</span> <span>Yesterday at 7:18 PM</span><br />
                  Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
                  Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)
              </Link>
              <br />
              23 Likes<br />
          </li>
          <li className="list-group-item">
              <span className="glyphicon glyphicon-small glyphicon-tower"></span>&nbsp;Another Organization<br />{/* TODO icon-org-placeholder */}
              <span>opposes</span> <span>Yesterday at 2:34 PM</span><br />
              Integer ut bibendum ex. Suspendisse eleifend mi accumsan, euismod enim at, malesuada nibh.
              Duis a eros fringilla, dictum leo vitae, vulputate mi. Nunc vitae neque nec erat fermentum... (more)<br />
              5 Likes<br />
          </li>
        </ul>
    </div>
    <BallotMajorNavigation />
</div>
		);
	}
}
