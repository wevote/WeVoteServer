from voter.models import VoterManager


def create_dev_user():
    fName = "Samuel"
    lName = "Adams"
    email = "samuel@adams.com"
    password = "ale"
    # Uncomment to set up this user in the database by visiting http://localhost:8000/voter/create_dev_user
    # VoterManager().create_developer(fName, lName, email, password)

