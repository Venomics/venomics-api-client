import os
import requests
import time
from pprint import pprint
import json


def poll_job(s, venomics_url, job):
    # TODO: add timeout
    while job['status'] not in (3,4):
        response = s.get('{}/jobs/{}'.format(venomics_url, job['id']))
        job = response.json()['job']
        time.sleep(1)

    if job['status'] == 3:
        return job['query_result_id']

    return None


def get_fresh_query_result(venomics_url, query_id, api_key, params):
    s = requests.Session()
    s.headers.update({'Authorization': 'Key {}'.format(api_key)})

    payload = dict(max_age=0, parameters=params)

    response = s.post('{}/queries/{}/results'.format(venomics_url, query_id), data=json.dumps(payload))

    if response.status_code != 200:
        raise Exception('Refresh failed.')

    result_id = poll_job(s, venomics_url, response.json()['job'])

    if result_id:
        response = s.get('{}/queries/{}/results/{}.json'.format(venomics_url, query_id, result_id))
        if response.status_code != 200:
            raise Exception('Failed getting results.')
    else:
        raise Exception('Query execution failed.')

    return response.json()['query_result']['data']['rows']

if __name__ == '__main__':
    params = {'some_parameter': 1}
    query_id = 1234
    # Need to use a *user API key* here (and not a query API key).
    api_key = '...'
    pprint(get_fresh_query_result('https://www.venomics.xyz/acme', query_id, api_key, params))