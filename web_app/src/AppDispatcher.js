import {Dispatcher} from 'flux';

// we will be using flux initially until we
// can convert to reflux successfully
const flux = new Dispatcher();

export function register(callback) {
    return flux.register(callback);
}

export function waitFor(ids) {
    return flux.waitFor(ids);
}

/**
 * Dispatches a single action.
 */
export function dispatch(type, action = {}) {
    if (!type) throw new Error('You forgot to specify type.');

    flux.dispatch({type, ...action});
}

export function dispatchAsync(promise, types, action = {}) {
    const { request, success, failure } = types;

    dispatch(request, action);

    promise.then(
        response => dispatch(success, { ...action, response }),
        error => dispatch(failure, { ...action, error })
    );
}
