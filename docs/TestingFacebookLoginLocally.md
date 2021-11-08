# Testing Facebook Sign In with a Physical Tethered Phone in Cordova
The phone can't access localhost, so we need to run ngrok, and configure the webapp to access the local Python Server voa ngrok

In a terminal in PyCharm:

    (PycharmEnvironments) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 ~ % cd /Users/stevepodell/WebstormProjects/ngrok
    (PycharmEnvironments) stevepodell@Steves-MacBook-Pro-32GB-Oct-2109 ngrok % ./ngrok http 8000
    
    ngrok by @inconshreveable                                                                                                                                                 (Ctrl+C to quit)
                                                                                                                                                                                              
    Session Status                online                                                                                                                                                      
    Account                       stevepodell37@gmail.com (Plan: Free)                                                                                                                        
    Update                        update available (version 2.3.40, Ctrl-U to update)                                                                                                         
    Version                       2.3.35                                                                                                                                                      
    Region                        United States (us)                                                                                                                                          
    Web Interface                 http://127.0.0.1:4040                                                                                                                                       
    Forwarding                    http://d74f-2601-643-8400-5b80-7cad-2933-47a9-26ea.ngrok.io -> http://localhost:8000                                                                        
    Forwarding                    https://d74f-2601-643-8400-5b80-7cad-2933-47a9-26ea.ngrok.io -> http://localhost:8000                                                                       
                                                                                                                      

In the WebApp config.js file:

    WE_VOTE_SERVER_ROOT_URL: "http://d74f-2601-643-8400-5b80-7cad-2933-47a9-26ea.ngrok.io/",
    WE_VOTE_SERVER_ADMIN_ROOT_URL: "http://d74f-2601-643-8400-5b80-7cad-2933-47a9-26ea.ngrok.io/admin/",
    WE_VOTE_SERVER_API_ROOT_URL: "http://d74f-2601-643-8400-5b80-7cad-2933-47a9-26ea.ngrok.io/apis/v1/",
    WE_VOTE_SERVER_API_CDN_ROOT_URL: "http://d74f-2601-643-8400-5b80-7cad-2933-47a9-26ea.ngrok.io/apis/v1/",

Then you can debug WebApp code in Cordova on a physical iPhone with a local Python WeVoteServer.