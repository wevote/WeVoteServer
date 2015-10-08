let React = require("react");

require("stylesheets/bootstrap.3.3.1");

let SubMenu = React.createClass({
  render() {
    return (
      <div className="navbar">
        sub menu
      </div>
    );
  }
});

ReactDOM.render(<SubMenu />, document.getElementById('content'));
