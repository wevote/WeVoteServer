import React from "react";
import { Router, Link } from "react-router";

export default class BallotMajorNavigation extends React.Component {
  render() {
    return <div className="row">
        <div className="navbar navbar-default navbar-fixed-bottom">
            <div className="container-fluid container-top10 seperator-top">
              <div className="row">
                <Link to="ballot">
                    <div className="col-xs-2 center-block text-center">
                      <span className="glyphicon glyphicon-list-alt glyphicon-line-adjustment"></span><br />
                      <span className="text-center small">Ballot</span>
                    </div>
                </Link>
                <div className="col-xs-2 center-block text-center">
                  <span className="glyphicon glyphicon-inbox glyphicon-line-adjustment"></span><br />
                  <span className="text-center small">Requests</span>
                </div>
                <div className="col-xs-2 center-block text-center">
                  <span className="glyphicon icon-icon-connect-1-3"></span><br />
                  <span className="text-center small">Connect</span>
                </div>
                <div className="col-xs-3 center-block text-center">
                  <span className="glyphicon icon-icon-activity-1-4"></span><br />
                  <span className="text-center small">Activity</span>
                </div>
                <Link to="more">
                    <div className="col-xs-2 center-block text-center">
                      <span className="glyphicon glyphicon-menu-hamburger glyphicon-line-adjustment"></span><br />
                      <span className="text-center small">More</span>
                    </div>
                </Link>
              </div>
            </div>
        </div>
    </div>
  }
}
