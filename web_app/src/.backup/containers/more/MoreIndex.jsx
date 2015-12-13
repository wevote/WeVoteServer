import React, {PropTypes} from 'react';

export default class MoreIndex extends React.Component {
    static propTypes = {
        children: PropTypes.object
    }

    render () {
        return (
            <div className="MoreIndex">
                {this.props.children}
            </div>
        );
    }
}
