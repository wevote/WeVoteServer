import React from "react";

export default class HomePage extends React.Component {
	static getProps() {
		return {};
	}
	render() {
    return <div className="container-fluid well well-40">
      <h2 className="text-center">We Vote Social Voter Guide</h2>
      <ul className="list-group">
        <li className="list-group-item">Research ballot items</li>
        <li className="list-group-item">Learn from friends</li>
        <li className="list-group-item">Take to the polls</li>
      </ul>

      <ul className="list-group">
          <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;Neutral and private</li>
          <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;123,456 voters</li>
          <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;417 not-for-profit organizations</li>
          <li className="list-group-item"><span className="glyphicon glyphicon-small glyphicon-ok-sign"></span>&nbsp;and you.</li>
      </ul>
      <div className="input-group">
        <label htmlFor="last-name">My Ballot Location</label><br />
        <span className="small">This is our best guess - feel free to change</span>
        <input type="text" name="last-name" className="form-control" />
      </div>
		</div>;
	}
}
