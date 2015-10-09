import React from "react";
import { Link } from "react-router";

//TODO: break apart the number of components in here
export default class MainMenu extends React.Component {
	render() {
		return <div className="row">
      <nav className="navbar navbar-main">
        <div className="container-fluid">
          <form className="navbar-form" role="search">
            <div className="input-group input-group-lg">
              <input type="text" className="form-control input-lg" placeholder="Search" />
            </div>
          </form>
        </div>
      </nav>
		</div>;
	}
}
