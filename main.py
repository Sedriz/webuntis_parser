import json

import requests
from datetime import datetime
from argparse import ArgumentParser

ELEMENT_ID = 12741
BASE_URL = 'https://mese.webuntis.com/'
API_URL = BASE_URL + 'WebUntis/api/'

jwt_token = ''


def get_date_obj(date: str, time: str):  # 20230203 950
    date_time_str = f'{date} {time}'
    return datetime.strptime(date_time_str, '%Y%m%d %H%M')


def get_formatted_date_time(date: str, time: str):
    date_obj = get_date_obj(date, time)
    return date_obj.strftime("%Y-%m-%dT%H:%M:%S")


def get_formatted_time(time: str):
    date_obj = get_date_obj('19700101', time)
    return date_obj.strftime("%H:%M")


def get_formatted_date(date: str):
    date_obj = get_date_obj(date, '001')
    return date_obj.strftime("%Y-%m-%d")


def form_student_group(student_group: str):
    return student_group.split('_')[0]


def get_auth_token(j_session_id: str):  # Implement cache
    url = API_URL + "token/new"
    header = {
        'Cookie': f'JSESSIONID={j_session_id};',
    }
    res = session.get(url=url, headers=header)
    if res.status_code != 200:
        raise Exception(res.text)
    return res.text


def get_calendar_week(j_session_id: str, school_name: str, date_str: str, element_id: int):
    url = API_URL + "public/timetable/weekly/data"
    params = {
        'elementType': 5,
        'elementId': element_id,
        'date': date_str,
        'formatId': 1
    }
    header = {
        'Cookie': f'JSESSIONID={j_session_id}; schoolname="{school_name}"; traceId=238a78187d399beff69cdbbd5bbaf00b38e4e10f',
    }

    r = session.get(url=url, params=params, headers=header)
    if r.status_code != 200:
        raise Exception(r.text)
    return r.json()


def get_period_detail(j_session_id: str, period_date: str, period_start_time: str, period_end_time: str, element_id):
    url = API_URL + 'rest/view/v1/calendar-entry/detail'
    params = {
        'elementType': 5,
        'elementId': element_id,
        'endDateTime': get_formatted_date_time(period_date, period_end_time),  # '2023-01-30T08:45:00',
        'startDateTime': get_formatted_date_time(period_date, period_start_time),  # '2023-01-30T08:00:00',
        'homeworkOption': 'DUE'
    }
    headers = {
        'Authorization': f'Bearer {get_auth_token(j_session_id)}'
    }
    r = session.get(url=url, params=params, headers=headers)
    if r.status_code != 200:
        raise Exception(r.text)
    return r.json()


parser = ArgumentParser()
parser.add_argument("-js", "--j_session_id",
                    dest="j_session_id",
                    help="JSESSIONID from browser",
                    required=True)

parser.add_argument("-d", "--date",
                    dest="date",
                    help="A day in the week you want to get the week. Format: '2023-01-25'",
                    required=True)

parser.add_argument("-sn", "--school_name",
                    dest="school_name",
                    help="The name of your school. Can be found in browser. default: IT-Schule Stuttgart",
                    default='_aXQtc2NodWxlIHN0dXR0Z2FydA==')

args = parser.parse_args()

session = requests.Session()

# session.proxies = {
#     'http': 'proxy.its-stuttgart.de:3128',
#     'https': 'proxy.its-stuttgart.de:3128', }

calendarWeek = get_calendar_week(args.j_session_id, args.school_name, args.date, ELEMENT_ID)
data = calendarWeek['data']['result']['data']
elementPeriods = data['elementPeriods']
weekPeriods = elementPeriods[str(ELEMENT_ID)]

periodDict = {}

for period in weekPeriods:
    period_date = str(period['date'])
    formatted_period_date = get_formatted_date(period_date)
    periodStartTime = period['startTime']
    periodEndTime = period['endTime']
    periodStudentGroup = form_student_group(period['studentGroup'])
    period_list = periodDict.get(formatted_period_date)
    is_period_exam = period['cellState'] == 'EXAM'

    if not period_list:
        periodDict.update({
            formatted_period_date: []
        })
        period_list = periodDict.get(formatted_period_date)

    periodRes = get_period_detail(args.j_session_id, period_date, periodStartTime, periodEndTime, ELEMENT_ID)

    calendarEntries = periodRes['calendarEntries']
    teachingContent = calendarEntries[0]['teachingContent']

    period_list.append({
        'startTime': get_formatted_time(periodStartTime),
        'endTime': get_formatted_time(periodEndTime),
        'lesson': periodStudentGroup,
        'content': teachingContent or '',
        'exam': is_period_exam
    })

for key, value in periodDict.items():
    sorted_list = sorted(value, key=lambda d: d['startTime'])

    for period in sorted_list:
        double_periods = filter(lambda obj:
                                obj['content'] == period['content']
                                and obj['lesson'] == period['lesson']
                                and obj['startTime'] != period['startTime'], sorted_list)

        for double_period in double_periods:
            period['endTime'] = double_period['endTime']
            sorted_list.remove(double_period)

    periodDict.update({
        key: sorted_list
    })

period_json = json.dumps(periodDict, indent=4)

print(period_json)
