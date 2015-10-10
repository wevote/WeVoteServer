import React from "react";

export default class HomePage extends React.Component {
	static getProps() {
		return {};
	}
	render() {
    return <div className="container-fluid well">
      <h2>We Vote Social Voter Guide</h2>
      <ul>
        <li>Research ballot items</li>
        <li>Learn from friends</li>
        <li>Take to the polls</li>
      </ul>
      <div className="">
        <div><span className="glyphicon glyphicon-ok-sign"></span>Neutral and private</div>
        <div><span className="glyphicon glyphicon-ok-sign"></span>123,456 voters</div>
        <div><span className="glyphicon glyphicon-ok-sign"></span>417 not-for-profit organizations</div>
        <div><span className="glyphicon glyphicon-ok-sign"></span>and you.</div>
      </div>
      <div className="input-group">
        <label for="last-name" class="sr-only">My Ballot Location</label><br />
        <span>This is our best guess - feel free to change</span>
			  <input type="text" name="last-name" className="form-control" />
      </div>
		</div>;
	}
}
