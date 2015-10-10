import React from "react";

export default class HomePage extends React.Component {
	static getProps() {
		return {};
	}
	render() {
		return <div className="container-fluid col-md-offset-5">
      <div className="input-group">
        <label for="first-name" class="sr-only">First Name</label>
			  <input type="text" name="first-name" className="form-control" />
      </div>
      <div className="input-group">
        <label for="last-name" class="sr-only">Last Name</label>
			  <input type="text" name="last-name" className="form-control" />
      </div>
      <div className="input-group">
        <label for="email" class="sr-only">Email address</label>
			  <input type="text" name="email" className="form-control" />
      </div>
		</div>;
	}
}
