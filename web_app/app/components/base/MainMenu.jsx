import React from "react";
import { Link } from "react-router";

//TODO: break apart the number of components in here
export default class MainMenu extends React.Component {
	render() {
		return <div className="row">
      <nav className="navbar navbar-main">
        <div className="container-fluid">
          <input type="text" className="form-control input-lg" placeholder="Search" />
        </div>
      </nav>
		</div>;
	}
}
