// Ballot store will hold ballot data
import { register } from 'AppDispatcher';
import { mergeIntoStore, createStore } from 'utils/createStore';
import { BallotConstants } from 'constants/BallotConstants';
import { each } from 'underscore';

const _ballots = {};

/**
 * add data into store via mergeIntoStore
 * @param {Object} data data from server to merge
 */
function add (data) {
    mergeIntoStore(_ballots, data);
}

const BallotStore = createStore({
    /**
     * get ballot by id
     * @param  {String} ballot_id id of ballot
     * @return {Object} ballot data item
     */
    get (ballot_id) {
        return _ballots[ballot_id];
    },

    /**
     * @return {Array} array of Ballot Data
     */
    toArray () {
        var ballots = [];
        each(_ballots, (val, key) =>
            ballots.push(_ballots[key])
        );
        return ballots;
    }
});

export default BallotStore;

register ( action => {
    switch (action.actionType) {
        case BallotConstants.BALLOT_ADD:
            add(action.ballots);
            BallotStore.emitChange();
            break;
    }
});
