# import_export_twitter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/models.py for routines that manage internal twitter data

# https://dev.twitter.com/overview/api/users

# https://dev.twitter.com/overview/general/user-profile-images-and-banners
# Variant	Dimensions	Example URL
# normal	48px by 48px	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_normal.png
# bigger	73px by 73px	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_bigger.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_bigger.png
# mini	24px by 24px	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_mini.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3_mini.png
# original	original	http://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3.png
# https://pbs.twimg.com/profile_images/2284174872/7df3h38zabcvjylnyfe3.png
# Omit the underscore and variant to retrieve the original image. The images can be very large.
