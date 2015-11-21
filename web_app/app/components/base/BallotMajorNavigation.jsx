import React from "react";
import { Router, Link } from "react-router";

export default class BallotMajorNavigation extends React.Component {
  render() {
    return <div className="row">
        <div className="navbar navbar-default navbar-fixed-bottom">
            <div className="container-fluid container-top10 seperator-top">
              <div class="row">
                <Link to="ballot">
                    <div className="col-xs-3 center-block text-center">
                      <span className="glyphicon glyphicon-list-alt"></span><br />
                      <span className="text-center">My Ballot</span>
                    </div>
                </Link>
                <div className="col-xs-2 center-block text-center">
                  <span className="glyphicon glyphicon-inbox"></span><br />
                  <span className="text-center">Requests</span>
                </div>
                <div className="col-xs-2 center-block text-center">
                  <span className="glyphicon icon-icon-connect-1-3"></span><br />
                  <span className="text-center">Connect</span>
                </div>
                <div className="col-xs-3 center-block text-center">
                  <span className="glyphicon icon-icon-activity-1-4"></span><br />
                  <span className="text-center">Activity Feed</span>
                </div>
                <Link to="more">
                    <div className="col-xs-2 center-block text-center">
                      <span className="glyphicon glyphicon-menu-hamburger"></span><br />
                      <span className="text-center">More</span>
                    </div>
                </Link>
              </div>
            </div>
        </div>
    </div>
  }
}
