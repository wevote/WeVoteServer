"use strict";

import { Button, ButtonToolbar } from "react-bootstrap";
import React from "react";
import { Router, Link } from "react-router";

export default class BottomContinueNavigation extends React.Component {
    render() {
        var continue_text;
        if (this.props.continue_text) {
            continue_text = this.props.continue_text;
        } else {
            continue_text = 'Continue >';
        }
        var cancel_button;
        if (this.props.cancel_text) {
            cancel_button = <Button bsStyle="default">{this.props.cancel_text}</Button>;
        } else {
            cancel_button = '';
        }
        var link_route;
        if (this.props.link_route) {
            link_route = this.props.link_route;
        } else {
            link_route = 'ballot';
        }
        var alignCenter = {
            margin: 'auto',
            width: '100%'
        };
        return (
<div className="row">
    <div className="navbar navbar-default navbar-fixed-bottom">
        <div className="container-fluid container-top10 seperator-top">
            <Link to={ link_route }>
                <div className="row">
                    <div className="col-xs-2 center-block text-center" style={alignCenter}>
                        {cancel_button}&nbsp;
                        <Button bsStyle="primary">{continue_text}</Button>
                    </div>
                </div>
            </Link>
        </div>
    </div>
</div>
        );
    }
}
