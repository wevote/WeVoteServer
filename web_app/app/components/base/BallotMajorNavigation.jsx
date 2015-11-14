import React from "react";
import Router from "react-router";

var Link = Router.Link;

export default class BallotMajorNavigation extends React.Component {
  render() {
    return <div className="row">
        <div className="navbar navbar-default navbar-fixed-bottom">
            <div className="container-fluid container-top10 seperator-top">
                <Link to="ballot">
                    <div className="col-xs-6 col-sm-3 center-block text-center">
                      <span className="glyphicon glyphicon-list-alt"></span><br />
                      <span className="text-center">My Ballot</span>
                    </div>
                </Link>
                <div className="col-xs-6 col-sm-3 center-block text-center">
                  <span className="glyphicon glyphicon-inbox"></span><br />
                  <span className="text-center">Requests</span>
                </div>
                <div className="col-xs-6 col-sm-3 center-block text-center icon_connect">
                  <span className="icon_connect"></span><br />
                  <span className="text-center">Connect</span>
                </div>
                {/*<div className="col-xs-6 col-sm-3 center-block text-center">
                  <span className="glyphicon glyphicon-globe"></span><br />
                  <span className="text-center">Activity Feed</span>
                </div>*/}
                <Link to="more">
                    <div className="col-xs-6 col-sm-3 center-block text-center">
                      <span className="glyphicon glyphicon-menu-hamburger"></span><br />
                      <span className="text-center">More</span>
                    </div>
                </Link>
            </div>
        </div>
    </div>
  }
}
