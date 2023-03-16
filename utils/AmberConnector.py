"""Connector class with useful functions for AmberScript
"""
import requests
import json
import os.path
from utils import utils


class AmberConnector():
    def __init__(self, token):
        print("Amberscript connector.")
        self._token = token


    @property
    def jobs(self):
        url = "https://api.amberscript.com/api/jobs"
        querystring = {"apiKey":self._token}
        payload = ""
        response = requests.request("GET", url, data=payload, params=querystring)
        if self._status_response(response) in range(200, 300):
            return self._content_response(response)
        else:
            raise Exception("HTTP ERROR "+str(self._status_response(response))+ \
                                          str(self._content_response(response)))


    @property
    def glossaries(self):
        url = "https://api.amberscript.com/api/glossary"
        querystring = {"apiKey":self._token}
        payload = ""
        response = requests.request("GET", url, data=payload, params=querystring)
        if self._status_response(response) in range(200, 300):
            return self._content_response(response)
        else:
            raise Exception("HTTP ERROR "+str(self._status_response(response))+ \
                                          str(self._content_response(response)))


    def _status_response(self, response):
        return response.status_code


    def _content_response(self, response):
        return json.loads(response.text)


    def _text_response(self, response):
        return response.text



    def get_job_status(self, job_id):
        url = "https://api.amberscript.com/api/jobs/status"
        querystring = {"jobId":job_id,"apiKey":self._token}
        payload = ""
        response = requests.request("GET", url, data=payload, params=querystring)
        if _status_response(response) in range(200, 300):
            return _content_response(response)
        else:
            raise Exception("HTTP ERROR "+str(_status_response(response))+ \
                                          str(_content_response(response)))

    def submit_job(self, data, glossary_id = None):
        url = 'https://api.amberscript.com/api/jobs/upload-media'
        if glossary_id:
            querystring = {"jobType":"direct","language":"en",
                           "transcriptionType":"transcription", 
                           "glossaryId":glossary_id,
                           "apiKey":self._token}
        else:
            querystring = {"jobType":"direct","language":"en",
                           "transcriptionType":"transcription",
                           "apiKey":self._token}

        files = {'file': open(data, 'rb')}
        response = requests.post(url, files=files, verify=False, params=querystring)
        if self._status_response(response) in range(200, 300):
            return self._content_response(response)
        else:
            raise Exception(
                "HTTP ERROR "+str(self._status_response(response))+ \
                              str(self._content_response(response)))


    def get_results_txt(self, job_id):
        url = "https://api.amberscript.com/api/jobs/export-txt"
        querystring = {"jobId":job_id, "apiKey":self._token}
        payload = ""
        response = requests.request("GET", url, data=payload, params=querystring)
        if self._status_response(response) in range(200, 300):
            return self._text_response(response)
        else:
            raise Exception(
                "HTTP ERROR "+str(self._status_response(response))+ \
                              str(self._content_response(response)))
