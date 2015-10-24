import React from 'react';
import Router from 'react-router';

const Search = React.createClass({
  propTypes: {
    searchText: React.PropTypes.string.isRequired
  },
  mixins: [Router.Navigation],
  handleSearch() {
    const searchInput = this.refs.getDOMNode().value;
    this.refs.search.getDOMNode().value = 'Search';
    this.transitionTo('profile', {searcInput: searchInput});
  },
  render() {
    return (<div className="col-sm-12">
      <div className="input-group">
        <input type="text" className="form-control" ref="search" placeholder="Search" onBlur={this.handleSearch} />
      </div>
    </div>
  );
  }
});

module.exports = Search;
