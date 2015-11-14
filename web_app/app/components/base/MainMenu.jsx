import React from "react";
import { Link } from "react-router";

//TODO: break apart the number of components in here
export default class MainMenu extends React.Component {
	render() {
		return <div className="row">
            <nav className="navbar navbar-main navbar-fixed-top">
                <div className="container-fluid">
                    <div className="left-inner-addon">
                        {/*<i className="glyphicon glyphicon-search icon-search"></i>*/}
                        {/*<input type="text" className="form-control input-lg" placeholder="Search" />*/}
                </div>
            </div>
      </nav>
		</div>;
	}
}
