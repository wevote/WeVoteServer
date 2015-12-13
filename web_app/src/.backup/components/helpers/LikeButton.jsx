import React from "react";

var LikeButton = React.createClass({
	getInitialState: function () {
		return {liked: false};
	},
	handleClick: function(event) {
		this.setState({liked: !this.state.liked});
	},
	render: function () {
		return (
			<span onClick={this.handleClick}></span>
		);
	}
});

React.render(<LikeButton />, document.getElementById('content'));