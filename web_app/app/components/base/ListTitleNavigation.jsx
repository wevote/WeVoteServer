"use strict";

import React from "react";
import { Link } from "react-router";

export default class ListTitleNavigation extends React.Component {
	render() {
        var back_to_text;
        if (this.props.back_to_text) {
            back_to_text = this.props.back_to_text;
        } else {
            back_to_text = '&lt; Back';
        }
        var back_to_link;
        if (this.props.back_to_on) {
            back_to_link = <div className="left-inner-addon">
                {/* Switch between "Back" and "Back to My Ballot" */}
                <p className="text-left"><Link to="ballot">{back_to_text}</Link></p>
            </div>;
        }
        var header_text;
        if (this.props.header_text) {
            header_text = this.props.header_text;
        } else {
            header_text = '';
        }
		return (
<div className="row">
    <nav className="navbar navbar-main navbar-fixed-top">
        <div className="container-fluid">
            {back_to_link}
            <div className="left-inner-addon">
                <h4 className="pull-left no-space bold">{header_text}</h4>
            </div>
        </div>
    </nav>
</div>
        );
	}
}
