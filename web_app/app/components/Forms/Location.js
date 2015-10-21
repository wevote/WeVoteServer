import React from 'react';

var Location = React.createClass({
    propTypes: {
      location: React.PropTypes.string.isRequired
    },
    handleInput() {
      var newLocation = this.refs.getDOMNode().value;
      this.refs.location.getDOMNode.value = '';
      this.props.location(newLocation);
    }
    render() {
      return (
        <div className="row">
          <input type="text" className="form-control" ref="location" placeholder="Oakland, CA" />
        </div>
      )
    }
});

export default Location;
