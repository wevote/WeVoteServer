import requests
from bs4 import BeautifulSoup
import re

IMG_CLASS_NAME_WE_ARE_SEEKING = "widget-img"


# Retrieves the parsed HTML content from the given URL.
def get_parsed_html(url):
    try:
        page = requests.get(url)
        return BeautifulSoup(page.content, "html.parser")

    except requests.exceptions.RequestException:
        print('Unable to connect to {}'.format(url))
        return BeautifulSoup('', "lxml")

    # Parses the Ballotpedia page for all state legislature elections to get pages for individual states
    # Outputs list of ordered pairs:(url, state)


def get_state_elections_url(url):
    ballotpedia_page = url
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
              "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
              "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
              "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
              "Nebraska", "Nevada", "New_Hampshire", "New_Jersey", "New_Mexico", "New_York",
              "North_Carolina", "North_Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
              "Rhode_Island", "South_Carolina", "South_Dakota", "Tennessee", "Texas", "Utah",
              "Vermont", "Virginia", "Washington", "West_Virginia", "Wisconsin", "Wyoming"]

    html = get_parsed_html(ballotpedia_page)
    state_elections_info = set()
    for state in states:

        tags = html.find_all('a', href=re.compile('(?i){}.*elections,_2022'.format(state)))
        links = [requests.compat.urljoin(ballotpedia_page, tag.attrs['href']) for tag in tags]

        for link in links:
            state_elections_info.add((link, state))
    return state_elections_info


# This will extract candidate data from election page that is in a span of class "candidate"
def get_candidate_urls_page(url):
    soup = get_parsed_html(url)
    # Find all the HTML elements that contain the candidate names
    candidate_elements = soup.find_all("span", class_="candidate")
    # Extract the candidate names and construct the candidate URLs
    candidate_urls = []
    for element in candidate_elements:
        anchor_element = element.find("a")
        if anchor_element:
            candidate_urls.append(anchor_element['href'])

    return candidate_urls


# This will extract candidate data from election page that is in table data format of class "votebox-results-cell--text"
def get_candidate_urls_table(url):
    candidate_urls = []
    soup = get_parsed_html(url)
    candidate_elements = soup.find_all('td', class_='votebox-results-cell--text')
    for element in candidate_elements:
        candidate_link = element.find('a')['href']
        candidate_urls.append(candidate_link)
    return candidate_urls


# This will extract candidate image from list of candidate urls
def print_ballotpedia_photo_url_from_ballotpedia_candidate_urls(candidate_urls):
    for url in candidate_urls:
        soup = get_parsed_html(url)
        for img in soup.find_all(class_=IMG_CLASS_NAME_WE_ARE_SEEKING):
            img_url = img.get('src')  # Use get() method to safely retrieve attributes
            if img_url:
                print(img['alt'], img_url)
            else:
                print("Image URL not found for:", img['alt'])


def get_page_name(url):
    page_name = url.split(".org/")[-1].replace("_", " ")
    return page_name


# Function to retrieve all candidate images from state elections information.
def test_get_all_candidate_img_from_state_elections(url):
    print(get_page_name(url))
    state_elections_info = get_state_elections_url(url)
    for state in state_elections_info:
        print(state)
        candidate_urls = get_candidate_urls_page(state[0])
        print_ballotpedia_photo_url_from_ballotpedia_candidate_urls(candidate_urls)


# Function to retrieve all candidate images from state elections information.
def test_get_all_candidate_img_from_presidential_election(url):
    print(get_page_name(url))
    candidate_urls = get_candidate_urls_table(url)
    print_ballotpedia_photo_url_from_ballotpedia_candidate_urls(candidate_urls)


# Function to retrieve candidate image from candidate page
def test_get_candidate_img_from_single_candidate_page(url):
    print(get_page_name(url))
    candidate_url = [url]
    print_ballotpedia_photo_url_from_ballotpedia_candidate_urls(candidate_url)


def main():
    #test_get_all_candidate_img_from_state_elections("https://ballotpedia.org/State_legislative_elections,_2022")
    #test_get_all_candidate_img_from_presidential_election("https://ballotpedia.org/Presidential_election,_2024")

    test_get_candidate_img_from_single_candidate_page("https://ballotpedia.org/Joe_Biden")


main()
