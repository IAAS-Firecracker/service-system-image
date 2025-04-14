import requests 

def get_config(application_name,url):
    response = requests.get(f"{url}/{application_name}/profile")

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching config: {response.status_code}")