import axios from 'axios';
import ListTitleNavigation from "../../components/base/ListTitleNavigation";
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
        <h4>Display Guide</h4>
        <p>Search for more ballot items to include.
        </p>
        <br />
        <br />
	</div>
</div>
		);
	}
}
