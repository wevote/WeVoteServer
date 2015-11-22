import axios from 'axios';
import BallotReturnNavigation from "components/base/BallotReturnNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";

export default class AskOrSharePage extends React.Component {
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
	<BallotReturnNavigation back_to_ballot={false} />
	<div className="container-fluid well well-90">
		<h2 className="text-center">Ask or Share</h2>
		<div>
			<input type="text" name="ask_message" className="form-control"
				   defaultValue="Say or ask something about this..." /><br />
			<ul className="list-group">
				<li className="list-group-item">
					<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Fictional Candidate{/* TODO icon-person-placeholder */}
					<span className="glyphicon glyphicon-small glyphicon-star-empty"></span>{/* Right align */}
					<br />
					Running for US House - District 12&nbsp;<span className="glyphicon glyphicon-small glyphicon-info-sign"></span><br />
					{support_item}&nbsp;&nbsp;&nbsp;
					{oppose_item}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
					<br />
			 </li>
			</ul>
			<br />
			<br />
			<Input type="text" addonBefore="@" name="email_address" className="form-control" defaultValue="Enter email address(es) of friend(s) here" />
			<span>Separate email addresses with commas. We never sell email addresses.</span><br />
			<br />
			<br />
			<br />
			<br />
			These friends will see what you support, oppose, and which opinions you follow.<br />
			<Link to="ballot"><Button bsStyle="primary">Send</Button></Link>
		</div>
	</div>
</div>
		);
	}
}
