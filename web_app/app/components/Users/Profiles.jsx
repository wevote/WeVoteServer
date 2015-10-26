var React = require('react');
var Reflux = require('refulx');
var request = require('superagent');

var candidate = {
  "firstName": "John",
  "lastName": "Doe",
  "party": "Republican",
  "avatar": "find avatar to use"
};

var actions = Reflux.createActions(
  ["updateParty"]
)

var candidateStore = Reflux.createStore({
  data: {candidates: []},

  listenables: [actions],

  init() {
    request('http://localhost:8000/api/v1'), res => {
      this.data.candidate = res.body;
      this.trigger(this.data);
    },

    getInitialState() {
     return {candidate};
    }
  }

});

var Candidate = React.createClass({
  mixins: [Reflux.connect(store)],

  render() {
    return (<div>
     {this.state.candidate.map(person => {
        return (<h2>{c.firstName} {c.lastName}</h2>
          <h2>{c.party}</h2>
          <img src={c.avatar} />
        )})}
    </div>);
  }
});

module.exports = Candidate;
