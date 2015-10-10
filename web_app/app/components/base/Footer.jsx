import React from "react";
import Router from "react-router";

export default class Footer extends React.Component {
  render() {
    return <div className="row">
        <div className="navbar navbar-default navbar-fixed-bottom">
            <div className="container-fluid">
                <div className="col-xs-6 col-sm-3 center-block text-center">
                  <span className="glyphicon glyphicon-list-alt"></span><br />
                  <span className="text-center">My Ballot</span>
                </div>
                <div className="col-xs-6 col-sm-3 center-block text-center">
                  <span className="glyphicon glyphicon-question-sign"></span><br />
                  <span className="text-center">Questions</span>
                </div>
                <div className="col-xs-6 col-sm-3 center-block text-center">
                  <span className="glyphicon glyphicon-globe"></span><br />
                  <span className="text-center">News Feed</span>
                </div>
                <div className="col-xs-6 col-sm-3 center-block text-center">
                  <span className="glyphicon glyphicon-tasks"></span><br />
                  <span className="text-center">More</span>
                </div>
            </div>
        </div>
    </div>
  }
}
