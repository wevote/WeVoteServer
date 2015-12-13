import React, { Component, PropTypes } from "react";
import Navigator from 'components/Navigator';

export default class Application extends Component {
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
                { this.props.children }
                <Navigator />
		    </div>
        );
	}
}
