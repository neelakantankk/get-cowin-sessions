import requests
import urllib
import json
import logging
import logging.config
import sys
import datetime
import argparse
from calendar import monthrange
from random import choice

ROOT_URL = r'https://cdn-api.co-vin.in/api/'
DISTRICT_ENDPOINT = r'v2/appointment/sessions/public/findByDistrict'
DISTRICT_CALENDAR_ENDPOINT = r'v2/appointment/sessions/public/calendarByDistrict'
LIST_DISTRICTS_ENDPOINT = r'v2/admin/location/districts/'
LIST_STATES_ENDPOINT = r'v2/admin/location/states'
USER_AGENT_STRING = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
                     'Mozilla/5.0 (X11; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0',
                     'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9',
                     'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36']

HEADERS = {'Accept-Language':'en_US',
           'User-Agent':choice(USER_AGENT_STRING)}

def get_state_id(state_name):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    call_url = urllib.parse.urljoin(ROOT_URL,LIST_STATES_ENDPOINT)
    try:
        with open('states_list.json','r') as states_list_file:
            states_list = json.load(states_list_file)
    except (FileNotFoundError, json.JSONDecodeError):
        req = requests.get(call_url,headers=HEADERS)
        if req.status_code != 200:
            logger.error(f"{call_url} returned {req.status_code}")
            if req.status_code == 403:
                logger.error(f"403 FORBIDDEN")
            sys.exit(1)
        else:
            logger.debug(f"{call_url} : {req.status_code}")
            states_list = req.json()
            with open('states_list.json','w') as states_list_file:
                json.dump(states_list,states_list_file)

    state = [state for state in filter(lambda x:x['state_name']==state_name,states_list['states'])]
    if not state:
        possible_states = list(map(lambda x:x['state_name'],
                filter(lambda x:x['state_name'].find(state_name) != -1,states_list['states'])))
        logger.error(f"Could not find state {state_name}, try one of {possible_states}")
        sys.exit(1)
    else:
        logger.debug("Returning state id")
        return state[0]['state_id']


def get_districts(state_id):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    call_url = urllib.parse.urljoin(ROOT_URL,LIST_DISTRICTS_ENDPOINT)
    call_url = f"{call_url}{state_id}"
    try:
        with open(f"district_list_{state_id}.json",'r') as district_list_file:
            district_list = json.load(district_list_file)
    except (FileNotFoundError, json.JSONDecodeError):
        req = requests.get(call_url,headers=HEADERS)
        if req.status_code != 200:
            logger.error(f"{call_url} returned {req.status_code}")
            if req.status_code == 403:
                logger.error(f"403 FORBIDDEN")
            sys.exit(1)
        else:
            logger.debug(f"{call_url} : {req.status_code}")
            district_list = req.json()
            with open(f"district_list_{state_id}.json",'w') as district_list_file:
                json.dump(district_list, district_list_file)
    districts = list(map(lambda x: (x['district_id'],x['district_name']),district_list['districts']))
    logger.debug(f"Returning district list")
    return districts

def create_date_for_query(date,month,year):
    if date<10:
        date = f"0{date}"
    if month<10:
        month = f"0{month}"
    return f"{date}-{month}-{year}"

def get_for_district(call_url,dist_query,date_query):
    logger = logging.getLogger(__name__)
    query = {'district_id':f"{dist_query}",
             'date':f"{date_query}"}
    req = requests.get(call_url,headers=HEADERS,params=query)

    if req.status_code != 200:
        print(f"ERROR! {req.url} returned {req.status_code}")
        if req.status_code == 403:
            logger.error(f"403 FORBIDDEN")
            sys.exit(1)
        return None
    else:
        logger.debug(f"{call_url} : {req.status_code}")
        return req.json()

def get_day_for_district(dist_query,date_query):
    call_url = urllib.parse.urljoin(ROOT_URL,DISTRICT_ENDPOINT)
    res = get_for_district(call_url,dist_query, date_query)
    if res and res['sessions']:
        sites = parse_sessions(res['sessions'])
        if sites:
            print(f"{date_query:-^80}")
            info = list(map(lambda x:{'name':x['name'],'pincode':x['pincode'],'vaccine':x['vaccine'],'available':x['available_capacity']},sites))
            for center in info:
                print(f"{center['name']}: {center['pincode']} : {center['vaccine']}: {center['available']}")

   

def get_week_for_district(dist_query, date_query):
    logger = logging.getLogger(__name__)
    call_url = urllib.parse.urljoin(ROOT_URL,DISTRICT_CALENDAR_ENDPOINT)
    res = get_for_district(call_url,dist_query,date_query)
    info = dict()
    if res:
        for center in res['centers']:
            if center['sessions']:
                sessions_by_date = {session['date']:{'name':center['name'],'available':session['available_capacity'],'dose1':session['available_capacity_dose1'],
                                                     'pincode':center['pincode'],'vaccine': session['vaccine'],'fee':center['fee_type'],'address':center['address']}
                                                     for session in center['sessions'] if session['min_age_limit'] == 18 and session['available_capacity']>0 and
                                                     session['available_capacity_dose1']>0}
            for date in sorted(sessions_by_date.keys()):
                session = info.setdefault(date,[])
                session.append(sessions_by_date[date])
        logger.debug(f"Info --> {len(info)}")
        return info
    else:
        return None

def parse_sessions(raw_sessions):
    filtered_sessions = filter(lambda x: str(x["min_age_limit"]) == '18',raw_sessions)
    sites = [site for site in filtered_sessions]
    return sites


def main():
    logger = logging.getLogger()
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description="Get state for which to get vaccination slots. Default: Delhi")
    parser.add_argument('state',nargs='?',default='Delhi')
    args = parser.parse_args()
    logger.info(f"Getting slots for {args.state}")
    state_to_get = args.state
    state_id = get_state_id(state_to_get)
    districts = get_districts(state_id)

    TODAY = datetime.date.today()
    MAX_DAYS = monthrange(TODAY.year, TODAY.month)[1]

    for date in range(TODAY.day,MAX_DAYS+1,7):
        logger.info(f"Getting for week of {date}")
        date_query = create_date_for_query(date,TODAY.month,TODAY.year)
        sessions_this_week = dict()
        for dist_query,dist_name in districts:
            sessions_this_week[dist_name] = get_week_for_district(dist_query,date_query)
        for dist_name in sorted(sessions_this_week.keys()):
            print(f"{dist_name:-^80}")
            for date,sessions in sessions_this_week[dist_name].items():
                print(f"{date:-^80}")
                for session in sessions:
                    print(f"{session['name']} - {session['address']} - {session['pincode']} - {session['vaccine']} - {session['fee']} - {session['available']} - Dose 1: {session['dose1']}")


if __name__ == '__main__':
    main()
