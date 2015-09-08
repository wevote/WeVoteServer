/**
 * Authentication
 * @namespace wevoteusa.authentication.services
 */

(function () {
	'use strict';

	angular
		.module('vevoteusa.authentication.services')
		.factory('Authentication', Authentication);

	Authentication.$inject = ['$cookies', '$http'];

	/**
	 * @namespace Authentication
	 * @returns {Factory}
	 */
	
	function Authentication($cookies, $http) {
		/**
		 * @name Authentication
		 * @description The Factory to be returned
		 */
		
		var Authentication = {
			register: register 
		};

		return Authentication;


		/**
		 * @name register
		 * @param  {string} email    The email entered by the user
		 * @param  {string} password The password entered by the user
		 * @param  {string} username The username entered by the user
		 * @return {Promise}
		 */
		function register(email, password, username) {
			return $http.post('/api/v1/accounts/', {
				username: username,
				password: password,
				email: email
			});
		}
	} 
})();