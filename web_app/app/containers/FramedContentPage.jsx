import axios from 'axios';
import AskOrShareAction from "components/base/AskOrShareAction";
import OrganizationsToFollowList from "components/base/OrganizationsToFollowList";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";
import styles from "./FramedContentPage.css";  // Including this causes problems elsewhere in the site

export default class ConnectPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

	render() {
	    return (
<div>
	<div className="row">
		<nav className="navbar navbar-main navbar-fixed-top bottom-separator">
			<div className="container-fluid">
				<div className="left-inner-addon">
				  <Link to="about"><span className="glyphicon glyphicon-small glyphicon-remove"></span></Link>
				  <ul className="nav nav-pills pull-right">
					<li><AskOrShareAction link_text={'Share'} /></li>
				  </ul>
				</div>
			</div>
		</nav>
	</div>

    <iframe className="iframe_for_framed_content" src="http://www.WeVoteUSA.org" height="100%" width="100%" frameborder="0"></iframe>
</div>
		);
	}
}
