// Ballot store will hold ballot data
import { register } from 'AppDispatcher';
import { createStore } from 'utils/createStore';

const _ballots = {};

const BallotStore = createStore({
    get (ballot_id) {
        return _ballots[ballot_id];
    },

    // returns array of all ballots
    getAll () {
        var ballots = [];
        Object.keys(_ballots)
            .forEach( key =>
                ballots.push(_ballots[key])
            );
        return ballots;
    }
});

BallotStore.dispatchToken = register( payload => {

});

export default BallotStore;
