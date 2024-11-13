import re

def find_in_page(doc):
    # window.csrfToken = "DwSsXuVc-uECsSv6dW5ifI4025HacsODuhb8"
    decoded_data = doc.decode('utf-8')
    token_search = re.search('window.csrfToken = "([^"]+)"', decoded_data, re.IGNORECASE)
    assert token_search, "No csrf token found in response"
    return token_search.group(1)