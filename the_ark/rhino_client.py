import logging
import requests
import json


class RhinoClient(object):

    json_headers = {'content-type': 'application/json'}

    def __init__(self, test_name, url, brand, branch, build_id, user,
                 rhino_client_url):
        """
        Initializes the test_data for the tests that created the client.
        All of the data, except the tests name, is created using the
        BaselineBase defaults for the build run being
        :param test_name: The name of the tests that is creating the client.
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self.rhino_url = f"http://{rhino_client_url}/api/"
        self.posted = False
        self.test_data = {
            "branch": branch,
            "brand": brand,
            "build_id": build_id,
            "test_type": test_name,
            "build_url": url,
            "user": user
        }

    def verify_data(self):
        """
        Ensures all data (except tests _id) is of type str
        This method can be used in the future for any other validation
        that needs to occur (string length, etc)
        """
        for key, value in self.test_data.items():
            if key != "test_id":
                self.test_data[key] = str(value)

    def get(self, test_id):
        """
        Performs a get to retrieve the information for a specific tests.
        :param test_id: The test_id created for the data when the post is made.
        This will likely be the self.test_id
        information from the current rhino client.
        :return: The tests data for the
        """
        r = requests.get(self.rhino_url + test_id)
        return r.json()

    def post(self):
        """
        Submits the self.test_data to rhino, creating a new line on the
        dashboard.
        The tests data then comes back with that line's tests id
        We change the self.posted value to True in order to know that
        the tests has been posted already.
        """
        self.verify_data()

        r = requests.post(self.rhino_url, data=json.dumps(self.test_data),
                          headers=self.json_headers)
        if r.status_code == 201:
            self.test_data = r.json()
        else:
            msg = f"Cannot POST {self.test_data} to {self.rhino_url}. Status Code: {r.status_code}"
            self.log.error(msg)
            raise RhinoClientException(msg)
        self.posted = True

    def put(self):
        """
        Updates an already existing Rhino tests object
        with any updates to the data
        """
        self.verify_data()

        # Only perform the put if a successful post has happened
        # during this run
        if self.posted:
            r = requests.put(self.rhino_url + str(self.test_data["test_id"]),
                             data=json.dumps(self.test_data),
                             headers=self.json_headers)
            # Check the status code of the request. Mostly for when working
            # off network or if S3 s down
            if r.status_code == 201:
                self.test_data = r.json()
            else:
                msg = f"Cannot PUT to {self.rhino_url}. Status Code: {r.status_code}"
                self.log.error(msg)
                raise RhinoClientException(msg)
        else:
            raise RhinoClientException("Cannot update a tests on rhino before "
                                       "doing the initial post.")

    def send_test(self, status):
        """
        Change the tests status and send it on up to Rhino
        A POST will be performed if the tests data has not already
        gotten posted.
        If it has then the data sent up previously will be updated
        with a PUT request
        """
        self.log.info("Sending " + self.test_data['test_type'] +
                      " result to Rhino: " + str(self.test_data))
        self.test_data["status"] = status
        if self.posted:
            self.put()
        else:
            self.post()

    def set_log(self, file_path, link_text):
        """
        Set the log parameters for the current tests' run
        :param file_path: The href for the link
        :param link_text: What the text of the link will say
        """
        self.test_data["result_url"] = file_path
        self.test_data["result_text"] = link_text


class RhinoClientException(Exception):
    def __init__(self, arg):
        self.msg = arg
