from voter.models import VoterManager


def create_dev_user():
    fName = "Ilona"
    lName = "Gogiashvili"
    email = "gogiashvili.ilona@gmail.com"
    password = "sophia2018"
    # Uncomment next line to set up this user in the database by visiting http://localhost:8000/voter/create_dev_user
    VoterManager().create_developer(fName, lName, email, password)

