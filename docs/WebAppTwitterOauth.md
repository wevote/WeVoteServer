# WebApp OAuth for Twitter on the API Server

## Twitter Developer Portal User authentication settings
https://developer.x.com/en/portal/projects/1498394651836891139/apps/23560910/auth-settings

App permissions
* Read and write, checked
* Request email from users, enabled

Type of App
* Web App, Automated App or Bot, checked

App info, Callback URI / Redirect URL
* https://wevotedeveloper.com:8000/apis/v1/twitterSignInRequest/
* https://wevotedeveloper.com:3000/twitter_sign_in
* https://wevotedeveloper.com:8000/apis/v1/twitterSignInStart/

## Obtaining Access Tokens using 3-legged OAuth flow (Oauth 1.0a)
https://developer.x.com/en/docs/authentication/oauth-1-0a/obtaining-user-access-tokens

## Tweepy OAuth 1.0a User Context
https://docs.tweepy.org/en/stable/authentication.html

## Steps (May 24, 2024)
1) WebApp sends twitterSignInStart
* Handled by twitter_sign_in_start_view, which calls
  * twitter_sign_in_start_for_api
  * Opens a  tweepy.OAuth1UserHandler
    * with callback url =  https://wevotedeveloper.com:8000/apis/v1/twitterSignInRequest/?voter_info_mode=0&voter_device_id=3C8dF2FQrJ2NiSEzFEqKV8b8siytRKY57SUISA3dVSRgOvtvzhOuKXP0da2jEUAxiQitJy9n7VIi6yoXPXljRyCz&return_url=https%3A%2F%2Fwevotedeveloper.com%3A3000%2Ftwitter_sign_in&cordova=False
    * receives request_token_dict = {'oauth_token': 'UQ9AoAAAAAABZ4LOAAABj6tiUEA', 'oauth_token_secret': 'xHFPZv7LBcdo9wLee9rkGvXRWC7yWNOz', 'oauth_callback_confirmed': 'true'}
    * saved to DB (id = 125) as 
      * twitter_request_token = 'UQ9AoAAAAAABZ4LOAAABj6tiUEA'
      * twitter_request_secret = 'xHFPZv7LBcdo9wLee9rkGvXRWC7yWNOz'
    * returns
      * twitter_authorization_url = 'https://api.twitter.com/oauth/authorize?oauth_token=UQ9AoAAAAAABZ4LOAAABj6tiUEA'
      * return_url = 'https://wevotedeveloper.com:3000/twitter_sign_in'
      * (returns to in inline in twitter_sign_in_start_view)
  * returns HttpResponse {'status': 'TWITTER_REDIRECT_URL_RETRIEVED ', 'success': True, 'voter_device_id': '3C8dF2FQrJ2NiSEzFEqKV8b8siytRKY57SUISA3dVSRgOvtvzhOuKXP0da2jEUAxiQitJy9n7VIi6yoXPXljRyCz', 'twitter_redirect_url': 'https://api.twitter.com/oauth/authorize?oauth_token=d46CIQAAAAABZ4LOAAABj6abjjQ', 'voter_info_retrieved': False, 'switch_accounts': False, 'cordova': False}
2) Screen shows https://api.twitter.com/oauth/authorize?oauth_token=UQ9AoAAAAAABZ4LOAAABj6tiUEA
  * On scteen:  Click the blue **Authorize app** button
3) In twitter_sign_in_request_view handler for twitterSignInRequest
  * Call twitter_sign_in_request_access_token_view
    * GET = <QueryDict: {'voter_info_mode': ['0'], 'voter_device_id': ['3C8dF2FQrJ2NiSEzFEqKV8b8siytRKY57SUISA3dVSRgOvtvzhOuKXP0da2jEUAxiQitJy9n7VIi6yoXPXljRyCz'], 'return_url': ['https://wevotedeveloper.com:3000/twitter_sign_in'], 'cordova': ['False'], 'oauth_token': ['UQ9AoAAAAAABZ4LOAAABj6tiUEA'], 'oauth_verifier': ['bVNijgVr05DOA9oGAJsvlk8sOrsVY0G5']}>
    * Calls twitter_sign_in_request_access_token_for_api
      * auth = tweepy.OAuth1UserHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
      * (L3019) auth.request_token set with values from QueryDict 'oauth_token': ['UQ9AoAAAAAABZ4LOAAABj6tiUEA'], 'oauth_verifier': ['bVNijgVr05DOA9oGAJsvlk8sOrsVY0G5']}
      * auth.get_access_token(incoming_oauth_verifier) 'bVNijgVr05DOA9oGAJsvlk8sOrsVY0G5'
        * auth.access_token = 'xHFPZv7LBcdo9wLee9rkGvXRWC7yWNOz'
        * auth.access_token_secret = 'GB9FOIZ82uYPgbDH7jhzRShLlsU17MFwQkWCxban3fYCs'
        * Save these values (L3052) in id 125 of twitter_auth_response
      * returns inline to twitter_sign_in_request_access_token_view
      * redirects to next_step_url https://wevotedeveloper.com:8000/apis/v1/twitterSignInRequest/?voter_info_mode=1&voter_device_id=PKawbz0SVpMLyfYaiZVUYzXLJ3i6SA0LTIIVewJOXIAk6Xp8F89vPwlTklZ3afWDytaOFZfmf57GWn9i0ulTjhmx&return_url=https%3A%2F%2Fwevotedeveloper.com%3A3000%2Ftwitter_sign_in&cordova=False
4) twitter_sign_in_request_view with voter_info_mode = '1'
  * Calls twitter_sign_in_request_voter_info_view(request)
    * Calls twitter_sign_in_request_voter_info_for_api
    * Loads twitter_auth_response id = 125
    * # WHAT IS THE POINT OF THIS?  Get me will provide info for the house account, not a client account
    * Twitter page says "Redirecting you back to the application. This may take a few moments."
5) In twitter_sign_in_request_voter_info_view(request):  # twitterSignInRequestVoterInfo (Step 3)
  * Supplemented return_url = https://wevotedeveloper.com:3000/twitter_sign_in/?oauth_verifier=bVNijgVr05DOA9oGAJsvlk8sOrsVY0G5&oauth_token=UQ9AoAAAAAABZ4LOAAABj6tiUEA
  * HttpResponseRedirect( to the return_url )
6) Signed in via Twitter in the WebApp

