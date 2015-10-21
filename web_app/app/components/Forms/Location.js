import React from 'react';

var Location = React.createClass({
    propTypes: {
      location: React.PropTypes.string.isRequired
    },
    render() {
      return (
        <div className="row">
          <input type="text" className="form-control" ref="location" placeholder="Oakland, CA" />
        </div>
      )
    }
});

export default Location;
