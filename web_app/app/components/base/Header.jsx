let React = require("react");

require("stylesheets/bootstrap.3.3.1.min");

let Header = React.createClass({
  render() {
    return (
      <div className="navbar navbar-default">
        Top navbar starter
      </div>
    );
  }
});

React.render(<Header />, document.getElementById('content'));
