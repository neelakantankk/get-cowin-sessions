import requests
import urllib
import json
import logging
import logging.config
import sys

ROOT_URL = r'https://cdn-api.co-vin.in/api/'
DISTRICT_ENDPOINT = r'v2/appointment/sessions/public/findByDistrict'
LIST_DISTRICTS_ENDPOINT = r'v2/admin/location/districts/'
LIST_STATES_ENDPOINT = r'v2/admin/location/states'
HEADERS = {'Accept-Language':'en_US'}

def get_state_id(state_name):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    call_url = urllib.parse.urljoin(ROOT_URL,LIST_STATES_ENDPOINT)
    try:
        with open('states_list.json','r') as states_list_file:
            states_list = json.load(states_list_file)
    except FileNotFoundError:
        req = requests.get(call_url,headers=HEADERS)
        if req.status_code != 200:
            logger.error(f"{call_url} returned {req.status_code}")
            sys.exit(1)
        else:
            states_list = req.json()
            with open('states_list.json','w') as states_list_file:
                json.dump(states_list,states_list_file)

    state = [state for state in filter(lambda x:x['state_name']==state_name,states_list['states'])]
    if not state:
        possible_states = map(lambda x:x['state_name'],
                filter(lambda x:x['state_name'].find(state_name) != -1,states_list['states']))
        logger.error("Could not find state {state_name}, try one of {possible_states}")
        sys.exit(1)
    else:
        logger.info("Returning state id")
        return state[0]['state_id']


def get_districts(state_id):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    call_url = urllib.parse.urljoin(ROOT_URL,LIST_DISTRICTS_ENDPOINT)
    call_url = f"{call_url}{state_id}"
    try:
        with open(f"district_list_{state_id}.json",'r') as district_list_file:
            district_list = json.load(district_list_file)
    except FileNotFoundError:
        req = requests.get(call_url,headers=HEADERS)
        if req.status_code != 200:
            logger.error(f"{call_url} returned {req.status_code}")
            sys.exit(1)
        else:
            district_list = req.json()
            with open(f"district_list_{state_id}.json",'w') as district_list_file:
                json.dump(district_list, district_list_file)
    districts = map(lambda x: x['district_id'],district_list['districts'])
    logger.info(f"Returning district list")
    return districts

def create_date_for_query(date,month,year):
    if date<10:
        date = f"0{date}"
    if month<10:
        month = f"0{month}"
    return f"{date}-{month}-{year}"

def get_for_district(dist_query,date_query):
    call_url = urllib.parse.urljoin(ROOT_URL,DISTRICT_ENDPOINT)
    query = {'district_id':f"{dist_query}",
             'date':f"{date_query}"}
    req = requests.get(call_url,headers=HEADERS,params=query)

    if req.status_code != 200:
        print(f"ERROR! {req.url} returned {req.status_code}")
        return None
    else:
        return req.json()

def parse_sessions(raw_sessions):
    filtered_sessions = filter(lambda x: str(x["min_age_limit"]) == '18',raw_sessions)
    for session in filtered_sessions:
        print(f"Name: {session['name']}",end=", ")
        print(f"PIN: {session['pincode']}")


def main():
    sessions = list()
    state_to_get = 'Delhi'
    state_id = get_state_id(state_to_get)
    districts = get_districts(state_id)
    for dist_query in districts:
        print(f"{dist_query:-^80}")
        for date in range(1,32):
            date_query = create_date_for_query(date,4,2021)
            res = get_for_district(dist_query,date_query)
            print(f"{date_query:-^80}")
            if res and res['sessions']:
                parse_sessions(res['sessions'])

if __name__ == '__main__':
    main()
