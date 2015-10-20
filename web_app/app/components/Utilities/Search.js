var React = require('react');
var Router = require('react-router');

var Search = React.createClass({
    mixins: [Router.Navigation],
    propTypes: {
      searchText = React.PropTypes.string.isRequired
    },
    handleSearch: function () {
      var searchInput = this.refs.getDOMNode().value;
      this.refs.search.getDOMNode().value = 'Search';
      this.transitionTo('profile', {searcInput: searchInput});
    }
    render: function () {
      return (
        <div class="col-sm-12">
          <div className="input-group">
            <input type="text" className="form-control" ref="search" placeholder="Search" onBlur={this.handleSearch} />
          </div>
        </div>
      );
    }
});

module.exports = Search;
