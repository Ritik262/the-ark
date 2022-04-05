import boto3
import mimetypes
import os
import shutil
import tempfile
import urllib
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import logging
import io

logger = logging.getLogger(__name__)

MAX_FILE_SPLITS = 9999
DEFAULT_FILE_SPLIT_SIZE = 6291456
DEFAULT_MINIMUM_SPLIT_AT_SIZE = 20000000


class S3Client(object):
    """A client that helps user to send and get files from S3"""
    s3_connection = None
    bucket = None

    def __init__(self, bucket):
        """
        Creates the logger and sets the bucket name that will be used throughout
        :param
            - bucket:   string - The name of the bucket you will be working with
        """
        self.bucket_name = bucket

    def connect(self):
        """Start the amazon connection using the system's boto.cfg file to retrieve the credentials"""
        if self.s3_connection:
            return

        try:
            self.s3_connection = boto3.client('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'])

        except Exception as s3_connection_exception:
            # - Reset the variables on failure to allow a reconnect
            self.s3_connection = None
            self.bucket_name = None
            message = f"Exception while connecting to S3: {s3_connection_exception}"
            raise message



    def store_file(self, s3_path, file_to_store, filename, return_url=False, mime_type=None):
        """
        Pushes the desired file up to S3 (e.g. log file).
        :param
            - s3_path:          string - The S3 path to the folder in which you'd like to store the file
            - file_to_store:    BytesIO or string - The fileIO or file local file path for the file to be sent
            - filename:         string - The name the file will have when on S3. Should include the file extension
            - return_url:       boolean - Whether to return the path to the file on S3
        :return
            - file_url:         string - The path to the file on S3. This is returned only is return_url is set to true
        """
        self.connect()

        try:
            s3_file_path = self._generate_file_path(s3_path, filename)
            if isinstance(file_to_store, io.BytesIO):
                file_type = type(file_to_store)
                if file_type in [str, bytes, io.BytesIO]:
                    self.s3_connection.put_object(Body=file_to_store, Bucket=self.bucket_name, Key=s3_file_path)
                else:
                    self.s3_connection.put_object(Body=file_to_store, Bucket=self.bucket_name, Key=s3_file_path)
            else:
                self.s3_connection.upload_file(file_to_store, self.bucket_name, s3_file_path)
            
            if return_url:
                file_url = self.s3_connection.generate_presigned_url('put_object', Params={'Bucket': self.bucket_name, 'Key': s3_file_path, 'ACL': 'public-read'}, ExpiresIn=360000)
                # Additional check for s3 AccessToken
                list_url = file_url.split('?')
                len_url = len(list_url)
                if len_url == 1:
                    return file_url
                elif len_url > 1:
                    return list_url[0]
                else:
                    return file_url

        except Exception as store_file_exception:
            message = f"Exception while storing file on S3: {store_file_exception}"
            raise message

    def get_file(self, s3_path, file_to_get):
        """
        Stores the desired file locally (e.g. configuration file).
        :param
            - s3_path:      string - The S3 path to the folder which contains the file
            - file_to_get:  string - The name of the file you are looking for in the folder
        :return
            - retrieved_file    StringIO - an IO object containing the content of the file retrieved from S3
        """
        self.connect()

        try:
            if self.verify_file(s3_path, file_to_get):
                retrieved_file = io.BytesIO()
                s3_file = self.bucket.get_key(
                    self._generate_file_path(s3_path, file_to_get))
                s3_file.get_contents_to_file(retrieved_file)
                return retrieved_file
            else:
                raise S3ClientException("File not found in S3")

        except Exception as get_file_exception:
            message = f"Exception while retrieving file from S3: {get_file_exception}"
            raise S3ClientException(message)

    def verify_file(self, s3_path, file_to_verify):
        """
        Verifies a file (e.g. configuration file) is on S3 and returns
        "True" or "False".
        :param
            - s3_path:          string - The S3 path to the folder which contains the file
            - file_to_verify:   string - The name of the file you are looking for in the folder
        :return
            - boolean:     True if .get_key returns an instance of a Key object and False if .get_key returns None:
        """
        self.connect()
        try:
            file_path = self._generate_file_path(s3_path, file_to_verify)
            s3_file = self.bucket.get_key(file_path)
            if s3_file:
                return True
            else:
                return False

        except Exception as verify_file_exception:
            message = f"Exception while verifying file on S3: {verify_file_exception}"
            raise S3ClientException(message)

    def _generate_file_path(self, s3_path, file_to_store):
        """
        Ensures that the / situation creates a proper path by removing any double slash possibilities
        :param
            - s3_path:       string - The path to the folder you wish to store the file in
            - file_to_store: string - The name of the file you wish to store
        :return
            - string:    The concatenated version of the /folder/filename path
        """
        return f"{(s3_path.strip('/'))}/{(file_to_store.strip('/'))}"

    def get_all_filenames_in_folder(self, path_to_folder):
        """
        Retrieves a list of the files/keys in a folder on S3
        :param
            - path_to_folder:   string - The path to the folder on S3. This should start after the bucket name
        :return
            - key_list: list - The list of keys in the folder
        """
        self.connect()

        s3_folder_path = str(path_to_folder)
        key_list = self.bucket.list(prefix=s3_folder_path)
        return key_list

    def get_most_recent_file_from_s3_key_list(self, key_list):
        """
        Sorts through the list of files in s3 key list object and returns the most recently modified file in the list
        :param
            - key_list:    list - The list of files returned from a s3.bucket.list() operation
        :return
            - key   boto.s3.Key - The most recently modified file in the key list
        """
        most_recent_key = None
        for key in key_list:
            if not most_recent_key or key.last_modified > most_recent_key.last_modified:
                most_recent_key = key
        return most_recent_key

    def _split_file(self, from_file, file_chunk_size=DEFAULT_FILE_SPLIT_SIZE):
        """
        Split a given file into smaller chunks named partXXXX into a temp at a default size of ~ 6 mb. The temp
        folder should be deleted after use.

        WARNING: You cannot split into more than 9999 files.

        :param
            - from_file:        string - the file to split up
            - file_chunk_size:  int - number of Bytes each split should contain (Should be > 5 MB for Amazon S3 minimum)
        :return:
            - temp_dir:         string - temp folder location of split file, use to iterate through the split files
        """
        if os.path.getsize(from_file) > (MAX_FILE_SPLITS * file_chunk_size):
            raise S3ClientException("Could not split the file.\nError: Input file is too large!\n")
        elif os.path.getsize(from_file) < DEFAULT_FILE_SPLIT_SIZE:
            raise S3ClientException("Could not split the file.\nError: Input file is too small!\n")

        try:
            temp_dir = tempfile.mkdtemp()
            part_num = 0
            with open(from_file, 'rb') as input_file:
                chunk = input_file.read(file_chunk_size)
                while chunk:
                    part_num += 1
                    open(os.path.join(temp_dir, ('part%04d' % part_num)), 'wb').write(chunk)
                    chunk = input_file.read(file_chunk_size)

            return temp_dir
        except Exception as e:
            raise S3ClientException("Could not split the file.\nError: {e}\n")


class S3ClientException(Exception):
    def __init__(self, message):
        self.msg = message

    def __str__(self):
        return self.msg
