import AskOrShareAction from "components/base/AskOrShareAction";
import axios from 'axios';
import BallotItemNavigation from "components/base/BallotItemNavigation";
import BallotMajorNavigation from "components/base/BallotMajorNavigation";
import React from "react";
import { Button, ButtonToolbar } from "react-bootstrap";
import { Link } from "react-router";

export default class BallotCandidateOnePositionPage extends React.Component {
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

        var like_item;
        if (this.props.like_on) {
            like_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-thumbs-up"></span>&nbsp;Like &nbsp;</Link>;
        } else {
            like_item = <Link to="ballot"><span className="glyphicon glyphicon-small glyphicon-thumbs-up"></span>&nbsp;Like &nbsp;</Link>;
        }
	    return (
<div>
	<BallotItemNavigation back_to_ballot={false} is_measure={false} />
	<div className="container-fluid well well-90">
        <ul className="list-group">
            <li className="list-group-item">
                <span className="icon_person"></span>&nbsp;Fictional Candidate
                <span className="glyphicon glyphicon-small glyphicon-star-empty"></span>{/* Right align */}
                <br />
                Running for US House - District 12&nbsp;<span className="glyphicon glyphicon-small glyphicon-info-sign"></span><br />
                {support_item}&nbsp;&nbsp;&nbsp;
                {oppose_item}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <AskOrShareAction />
                <br />
 				<div>
					<input type="text" name="address" className="form-control" defaultValue="What do you think?" />
                    <Link to="ballot_candidate" params={{id: 2}}><Button bsSize="small">Post Privately</Button></Link>
				</div>
         </li>
        </ul>

		<ul className="list-group">
		  <li className="list-group-item"><span className="icon_organization"></span>&nbsp;Organization Name<br />
		  supports<br />
		  3 minutes ago</li>
		  <li className="list-group-item">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis tempor vel
              mauris non convallis. Etiam vulputate libero vitae enim pretium, et lobortis nulla ultrices.
              Quisque at mi finibus, ullamcorper nulla et, bibendum nisl. Class aptent taciti sociosqu ad litora
              torquent per conubia nostra, per inceptos himenaeos. Ut suscipit sed justo eget molestie. Suspendisse
              molestie justo tristique vulputate posuere. Donec efficitur nunc vitae arcu aliquam, eget dignissim
              est fermentum. Mauris interdum dolor lacus, euismod convallis dui molestie id.</li>
		  <li className="list-group-item">
            {like_item}
            <AskOrShareAction />
              <br />
              23 people like this.
          </li>
		</ul>
	</div>
	<BallotMajorNavigation />
</div>
		);
	}
}
