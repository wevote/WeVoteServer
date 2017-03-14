# Donation System Setup (for testing donations on your local)

**If you've already updated your openssl and installed pyopenssl during the setup of your virtual environment, then you can skip to step 4**

In order to test Stripe transactions, your local will need to be updated to TLS1.2. For OS X, see instructions below.
For other operating systems go here (https://support.stripe.com/questions/how-do-i-upgrade-my-openssl-to-support-tls-1.2). 

For Mac OS X, type in your terminal:

1. `brew install openssl`

   After installation, check the version: `openssl version`
   
   If it's not showing 1.0.2 as the most recent version, then you need to symlink to the updated openssl version like so:
    
   * `ln -s /usr/local/Cellar/openssl/1.0.2h_1/bin/openssl /usr/local/bin/openssl `
   
   * open a new terminal window to continue:
   
2. `brew install python3`

	Reinitialize virtual environment in your WeVoteServer folder if the version of python you have installed is still
	pointing to the old openssl path (this might entail deleting bin/python and reinstalling python, then )
	 
	* `pip install -r requirements.txt ` (you might need to attempt pip install several times for it to fully install)
	
3. `python3 -m pip install pyopenssl pyasn1 ndg-httpsclient` 

4. `pip install stripe`


 
