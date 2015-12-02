import React, { PropTypes } from "react";

// style libraries
import 'font-awesome/css/font-awesome.css';
import 'bootstrap/dist/css/bootstrap.min.css';

import 'css/application.css';

import Navigator from 'components/Navigator';

export default class Application extends React.Component {
    static propTypes = {
        children: PropTypes.object
    };

    constructor(props) {
        super(props);
    }

	render() {
		return (
            <div>
                {/*Check and see if this is the users first time entering the site*/}
                {/* TODO:: ADD top nav, bottom nav... Global components in here... */}
                {/* Put loading logic back into this section here...*/}
			    {this.props.children}
                <Navigator />
		    </div>
        );
	}
}
