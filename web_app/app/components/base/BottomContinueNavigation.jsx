import { Button, ButtonToolbar } from "react-bootstrap";
import React from "react";
import { Router, Link } from "react-router";

export default class BottomContinueNavigation extends React.Component {
  render() {
    return (
<div className="row">
    <div className="navbar navbar-default navbar-fixed-bottom">
        <div className="container-fluid container-top10 seperator-top">
            <Link to="ballot">
                <div class="row">
                    <div className="col-xs-2 center-block text-center">
                        <Button bsStyle="primary">Continue ></Button>
                    </div>
                </div>
            </Link>
        </div>
    </div>
</div>
    );
  }
}
