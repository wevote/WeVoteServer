import React from "react";

export default class HomePage extends React.Component {
	static getProps() {
		return {};
	}
	render() {
		return <div className="container-fluid">
      <div className="input-group">
			  <input type="text" className="form-control" />
      </div>
      <div className="input-group">
			  <input type="text" className="form-control" />
      </div>
      <div className="input-group">
			  <input type="text" className="form-control" />
      </div>
		</div>;
	}
}
