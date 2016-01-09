"use strict";

import React from "react";
import { Link } from "react-router";

export default class HeaderBackNavigation extends React.Component {
    render() {
        var back_to_text;
        if (this.props.back_to_text) {
            back_to_text = this.props.back_to_text;
        } else {
            back_to_text = '< Back';
        }
        var link_route;
        if (this.props.link_route) {
            link_route = this.props.link_route;
        } else {
            link_route = 'ballot';
        }
        var back_to_on;
        if (this.props.back_to_off) {
            back_to_on = false;
        } else {
            back_to_on = true;
        }
        var back_to_link;
        if (back_to_on) {
            back_to_link = <span>
                {/* Switch between "< Back" and "Cancel" */}
                <Link to={link_route} params={this.props.params}>{back_to_text}</Link>
                &nbsp;&nbsp;&nbsp;&nbsp;
            </span>;
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
            <h4 className="text-center">{header_text}</h4>
        </div>
    </nav>
</div>
        );
    }
}
