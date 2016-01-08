import React from "react";
import { RouteHandler } from "react-router";

import styles from "./Application.css";

import { deviceIdGenerate } from '../service/api';

export default class Application extends React.Component {
    constructor(props) {
        super(props);
        deviceIdGenerate();
    }

	static getProps(stores, params) {
		var transition = stores.Router.getItem("transition");
		return {
			loading: !!transition
		};
	}
	render() {
		var { loading } = this.props;
		return <div className={styles.this + (loading ? " " + styles.loading : "")}>
			<div className={styles.loadingElement}>loading app...</div>
			<RouteHandler />
		</div>;
	}
}

Application.contextTypes = {
	stores: React.PropTypes.object
};
