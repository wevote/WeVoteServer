# README for API Installation: 6. Setup Initial Data

[Back to Install Table of Contents](README_API_INSTALL.md)


## Sample data
Sample data is provided. Go here:

    http://localhost:8000/admin
    
Find the "Sync Data with Master We Vote Servers" link, and click it: http://localhost:8000/admin/sync_dashboard/

Choose 1) an upcoming election from the drop down, and 2) your local state, and then run all scripts from top to bottom.
 
### Google Civic
In order to retrieve fresh ballot data, you will need to sign up for a Google Civic API key:

  - Go here:  https://console.developers.google.com/projectselector/apis/credentials?pli=1
  - Create a new project
  - Click Credentials -> New credentials -> API Key -> Browser Key
  - Check to make sure the "Google Civic Information API" is enabled here: https://console.developers.google.com/apis/enabled?project=atomic-router-681
  - If you don't see it, go here and search for "Google Civic": https://console.developers.google.com/apis/library?project=atomic-router-681
  - When you find it, click the "Enable API" button.
  - Copy your newly generated key and paste it into config/environment_variables.json as the value for GOOGLE_CIVIC_API_KEY
  
  
  * Note: if your email address is part of a G Suite domain, you may not have the admin access rights to create a project.  If so, logout of the G Suite account and use your personal account to create the project.
  
  
### Vote Smart
We also have a paid subscription with Vote Smart. You can sign up for a 
[Vote Smart developer key](http://votesmart.org/share/api/register#.VrIx4VMrJhE), or reach out to 
Dale.McGrew@WeVote.US to discuss using our organizational account.

  - Copy your Vote Smart key and paste it into config/environment_variables.json as the value for VOTE_SMART_API_KEY
  
### Twitter
Instructions coming soon.
    
[Working with WeVoteServer day-to-day](README_WORKING_WITH_WE_VOTE_SERVER.md)

[Back to Install Table of Contents](README_API_INSTALL.md)
