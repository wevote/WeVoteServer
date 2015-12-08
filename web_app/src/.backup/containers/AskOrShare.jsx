import React, { PropTypes } from 'react';

import { Link } from "react-router";
import { Input } from "react-bootstrap";

import BottomContinueNavigation from "components/base/BottomContinueNavigation";
import InfoIconAction from "components/base/InfoIconAction";
import ListTitleNavigation from "components/base/ListTitleNavigation";
import StarAction from "components/base/StarAction";

export default class AskOrShare extends React.Component {
	static propTypes = {
		support_on: PropTypes.object,
		oppose_on: PropTypes.object
	}
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
			    <ListTitleNavigation header_text={"Ask or Share"} back_to_on={true} back_to_text={"Cancel"} />
				<div className="container-fluid well well-90">
					<div>
						<input type="text" name="ask_message" className="form-control"
							   placeholder="Say or ask something about this..." /><br />
						<ul className="list-group">
							<li className="list-group-item">
			      				<StarAction we_vote_id={'wvcand001'} />
								<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Fictional Candidate{/* TODO icon-person-placeholder */}
			                	<InfoIconAction we_vote_id={'wvcand001'} />
								<br />
			      				<StarAction we_vote_id={'wvcand001'} />
								Running for US House - District 12
			                	<InfoIconAction we_vote_id={'wvcand001'} />
								<br />
								{support_item}&nbsp;&nbsp;&nbsp;
								{oppose_item}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
								<br />
						 	</li>
						</ul>
						<Input type="text" addonBefore="@" name="email_address" className="form-control" placeholder="Enter email address(es) of friend(s) here" />
						<span>These friends will see what you support, oppose, and which opinions you follow.</span><br />
						<br />
						<ul className="list-group">
							<li className="list-group-item">
								<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Friend Name{/* TODO icon-person-placeholder */}
						 	</li>
							<li className="list-group-item">
								<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Friend Name{/* TODO icon-person-placeholder */}
						 	</li>
							<li className="list-group-item">
								<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Friend Name{/* TODO icon-person-placeholder */}
						 	</li>
							<li className="list-group-item">
								<i className="icon-icon-add-friends-2-1 icon-light icon-medium"></i>&nbsp;Friend Name{/* TODO icon-person-placeholder */}
						 	</li>
						</ul>
						<br />
						<br />
						<br />
					</div>
				</div>
			    <BottomContinueNavigation link_route_continue={'ballot'} continue_text={'Send'} link_route_cancel={'ballot'} cancel_text={"cancel"} />
			</div>
		);
	}
}
