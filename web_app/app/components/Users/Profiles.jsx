var React = require('react');
var Reflux = require('reflux');
var request = require('superagent');

var candidate = {
  "firstName": "John",
  "lastName": "Doe",
  "party": "Republican",
  "avatar": "find avatar to use"
};

let actions = Reflux.createActions(
  ["updateParty"]
)

let candidateStore = Reflux.createStore({
  data: {candidates: []},

  listenables: [actions],

  init() {
    request('http://localhost:8000/api/v1', res => {
      this.data.candidate = res.body;
      this.trigger(this.data);
    });
  },

  getInitialState() {
    return {candidate};
  }

});

var Candidate = React.createClass({
  mixins: [Reflux.connect(store)],

  render() {
    return (<div>
      {this.state.candidate.map(person => {
        return (<div>
          <h2>{person.firstName} {person.lastName}</h2>
          <h2>{person.party}</h2>
          <img src={person.avatar} />
          </div>
      )})}
    </div>);
  }
});

module.exports = Candidate;
