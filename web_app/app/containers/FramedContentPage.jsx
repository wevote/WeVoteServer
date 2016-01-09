import axios from 'axios';
import FramedContentHeaderNavigation from "components/navigation/FramedContentHeaderNavigation";
import React from "react";
import { Button, ButtonToolbar, Input } from "react-bootstrap";
import { Link } from "react-router";
import FramedContentPageStyles from "./FramedContentPage.css";

export default class ConnectPage extends React.Component {
	constructor(props) {
		super(props);
	}

	static getProps() {
		return {};
	}

    componentDidMount() {
        {/* This allows the scroll bar to be used for the iframe */}
        {/* TODO: Once you visit this page and the component is mounted, scroll bars don’t work elsewhere in the app. */}
        if(document.body) {
            document.body.style.overflow = "hidden";
        }
    }

	render() {
	    return (
<div>
	<FramedContentHeaderNavigation />

    <iframe className={FramedContentPageStyles.iframe_for_framed_content} src="http://www.WeVoteUSA.org" height="100%" width="100%" frameborder="0"></iframe>
</div>
		);
	}
}
