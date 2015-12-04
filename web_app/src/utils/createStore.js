import EventEmitter from 'events';
import { each, isFunction } from 'underscore';

const CHANGE_EVENT = 'change';

export function createStore(spec) {
    var emitter = new EventEmitter();
    emitter.setMaxListeners(0);

    const store = Object.assign({
        emitChange() {
            emitter.emit(CHANGE_EVENT);
        },

        addChangeListener(callback) {
            emitter.on(CHANGE_EVENT, callback);
        },

        removeChangeListener(callback) {
            emitter.removeChangeListener(CHANGE_EVENT, callback);
        }

    },spec);

    each(store, (val, key) => {
        if (isFunction(val)) {
            store[key] = store[key].bind(store);
        }
    });

    return store;
}
