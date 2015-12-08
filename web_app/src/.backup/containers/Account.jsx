import React, {PropTypes} from 'react';

export default class Account extends React.Component {
    static propTypes = {
        children: PropTypes.object
    }

    render () {
        return (
            <div className="Account">
                {this.props.children}
            </div>
        );
    }
}
