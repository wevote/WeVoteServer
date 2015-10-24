var React = require('react');
var Reflux = require('refulx');

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
  listenables: [actions],

  onUpdateParty() {
    candidate.party = "add response party";
    this.trigger({candidate});
  },

  getInitialState() {
    return {candidate};
  }
});

var Candidate = React.createClass({
  mixins: [Reflux.connect(store)],

  render() {
    var c = this.state.candidate;

    return (<div>

      <h2>{c.firstName} {c.lastName}</h2>
      <h2>{c.party}</h2>
      <img src={c.avatar} />

      </div>);
  }
});

module.exports = Candidate;
