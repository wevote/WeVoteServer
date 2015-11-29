import axios from 'axios';
import FramedContentHeaderNavigation from "components/navigation/FramedContentHeaderNavigation";
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
	<FramedContentHeaderNavigation />

    <iframe className="iframe_for_framed_content" src="http://www.WeVoteUSA.org" height="100%" width="100%" frameborder="0"></iframe>
</div>
		);
	}
}
