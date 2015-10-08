let React = require("react");

require("stylesheets/bootstrap.3.3.1");

let Footer = React.createClass({
  render() {
    return (
      <div className="navbar navbar-default">
        footer
      </div>
    );
  }
});

ReactDOM.render(<Footer />, document.getElementById('content'));
