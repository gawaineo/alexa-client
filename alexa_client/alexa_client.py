"""
Python client class for interacting with Amazon Alexa Voice Service (AVS).
"""
import settings
import requests
import argparse
import json
import uuid
import time
import os
import re
from requests_futures.sessions import FuturesSession


class AlexaClient(object):
    def __init__(self, token=None, client_id=settings.CLIENT_ID,
            client_secret=settings.CLIENT_SECRET,
            refresh_token=settings.REFRESH_TOKEN,
            temp_dir=settings.TEMP_DIR, *args, **kwargs):
        self._token = token
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self.temp_dir = temp_dir
        os.system("mkdir -p {}".format(self.temp_dir))

    def get_token(self, refresh=False):
        """Returns AVS access token.

        If first call, will send a request to AVS to obtain the token
        and save it for future use.

        Args:
            refresh (bool): If set to True, will send a request to AVS
                            to refresh the token even if one's saved.

        Returns:
            AVS access token (str)
        """
        # Return saved token if one exists.
        if self._token and not refresh:
            return self._token
        # Prepare request payload
        payload = {
            "client_id" : self._client_id,
            "client_secret" : self._client_secret,
            "refresh_token" : self._refresh_token,
            "grant_type" : "refresh_token"
        }
        url = "https://api.amazon.com/auth/o2/token"
        res = requests.post(url, data=payload)
        res_json = json.loads(res.text)
        self._token = res_json['access_token']
        return self._token

    def get_request_params(self):
        """Returns AVS request parameters

        Returns a tuple of parameters needed for an AVS request.

        Returns:
            Tuple (url, headers, request_data) where,

               url (str): Request URL
               headers (dict): Request headers
               request_data (dict): Predefined request payload parameters
        """
        url = "https://access-alexa-na.amazon.com/v1"
        url += "/avs/speechrecognizer/recognize"
        headers = {'Authorization' : 'Bearer %s' % self.get_token()}
        request_data = {
            "messageHeader": {
                "deviceContext": [
                    {
                        "name": "playbackState",
                        "namespace": "AudioPlayer",
                        "payload": {
                            "streamId": "",
                            "offsetInMilliseconds": "0",
                            "playerActivity": "IDLE"
                        }
                    }
                ]
            },
            "messageBody": {
                "profile": "alexa-close-talk",
                "locale": "en-us",
                "format": "audio/L16; rate=16000; channels=1"
            }
        }
        return url, headers, request_data

    def process_alexa_response(self, res, save_to=None):
        """Saves the audio from AVS response to a file

        Parses the AVS response object and saves the audio to a file
        and returns the directives.

        Args:
            res (requests.Response): Response object from request.
            save_to (str): Filename including path for saving the
                           audio. If `None` a random filename will
                           be used and saved in the temporary directory.

        Returns:
            A tuple containing:
                - Path (str) to where the audio file is saved.
                - Json (str) of directives returned from AVS.
        """

        if res.status_code == requests.codes.ok:
            for v in res.headers['content-type'].split(";"):
                if re.match('.*boundary.*', v):
                    boundary =  v.split("=")[1]
            response_data = res.content.split(boundary)

            audio = None
            directives = None
            for d in response_data:
                # capture alexa directive in messageBody
                if 'application/json' in d:
                    message = d.split('\r\n')[3]
                    json_input = json.loads(message)
                    directives = json.dumps(json_input["messageBody"])
                if (len(d) >= 1024) and 'audio/mpeg' in d:
                    audio = d.split('\r\n\r\n')[1].rstrip('--')
            if audio:
                if not save_to:
                    save_to = "{}/{}.mp3".format(self.temp_dir, uuid.uuid4())
                with open(save_to, 'wb') as f:
                    f.write(audio)
            return (save_to, directives)

        # Raise exception for the HTTP status code
        print "AVS returned error: Status: {}, Text: {}".format(
            res.status_code, res.text)
        res.raise_for_status()

    def ask(self, audio_file, save_to=None):
        """
        Send a command to Alexa

        Sends a single command to AVS.

        Args:
            audio_file (str): File path to the command audio file.
            save_to (str): File path to save the audio response (mp3).

        Returns:
            File path for the response audio file (str).
        """
        with open(audio_file) as in_f:
            url, headers, request_data = self.get_request_params()
            files = [
                (
                    'file',
                    (
                        'request', json.dumps(request_data),
                        'application/json; charset=UTF-8',
                    )
                ),
                ('file', ('audio', in_f, 'audio/L16; rate=16000; channels=1'))
            ]
            res = requests.post(url, headers=headers, files=files)
            # Check for HTTP 403
            if res.status_code == 403:
                # Try to refresh auth token
                self.get_token(refresh=True)
                # Refresh headers
                url, headers, request_data = self.get_request_params()
                # Resend request
                res = requests.post(url, headers=headers, files=files)
            return self.process_alexa_response(res, save_to)

    def ask_multiple(self, input_list):
        """Sends multiple requests to AVS concurrently.

        Args:
            input_list (list): A list of input audio filenames to send
                               to AVS. The list elements can also be a
                               tuple, (in_filename, out_filename) to
                               specify where to save the response audio.
                               Otherwise the responses will be saved to
                               the temporary directory.

        Returns:
            List of tuples containing [(output_audio, json_directives)]
        """
        session = FuturesSession(max_workers=len(input_list))
        # Keep a list of file handlers to close. The input file handlers
        # need to be kept open while requests_futures is sending the
        # requests concurrently in the background.
        files_to_close = []
        # List of saved files and directives to return
        file_and_directives = []
        # List of future tuples, (future, output_filename)
        futures = []

        try:
            # Refresh token to prevent HTTP 403
            self.get_token(refresh=True)
            for inp in input_list:
                # Check if input is a tuple
                if isinstance(inp, tuple):
                    name_in = inp[0]
                    name_out = inp[1]
                else:
                    name_in = inp
                    name_out = None

                # Open the input file
                in_f = open(name_in)
                files_to_close.append(in_f)

                # Setup request parameters
                url, headers, request_data = self.get_request_params()
                files = [
                    (
                        'file',
                        (
                            'request', json.dumps(request_data),
                            'application/json; charset=UTF-8',
                        )
                    ),
                    (
                        'file',
                        ('audio', in_f, 'audio/L16; rate=16000; channels=1')
                    )
                ]

                # Use request_futures session to send the request
                future = session.post(url, headers=headers, files=files)
                futures.append((future, name_out))

            # Get the response from each future and save the audio
            for future, name_out in futures:
                res = future.result()
                response = self.process_alexa_response(res, name_out)
                file_and_directives.append(response)
            return file_and_directives
        except Exception as e:
            print str(e)
        finally:
            # Close all file handlers
            for f in files_to_close:
                f.close()

    def ask_series(self, input_list, delay=0):
        """Sends a series of requests to AVS.

        Args:
            input_list (list): A list of input full path audio filenames to send
                               to AVS. The list elements can also be a
                               tuple, (in_filename, out_filename) to
                               specify where to save the response audio.
                               Otherwise the responses will be saved to
                               the temporary directory.
            delay (int): Specify the number of seconds between each request.
                         defaults to zero.

        Returns:
            List of tuples containing [(output_audio, json_directives)]
        """
        file_and_directives = []
        pattern = re.compile(r".(\w+\.wav|pcm)$")
        for audio in input_list:
            if isinstance(audio, tuple):
                name_in = audio[0]
                name_out = audio[1]
            else:
                name_in = audio
                name_out = None

            audioMatch = re.search(pattern, name_in)
            if audioMatch:
                print ">>>Sending audio to Alexa AVS"
                try:
                    res = self.ask(name_in, save_to=name_out)
                    file_and_directives.append(res)
                    print "Audio output location: ", res
                except RuntimeError as e:
                    print "Error: ", e, "\nAudio sent: ", audio[0]
                print "---Finished sending audio---\n"
            else:
                print "Skipped: {} doesn't match expected audio format wav/pcm"\
                        .format(name_in)

            if delay > 0:
                print "{} second delay added".format(delay)
                time.sleep(delay)
        return file_and_directives

    def clean(self):
        """
        Deletes all files and directories in the temporary directory.
        """
        os.system('rm -r {}/*'.format(self.temp_dir))


def read_input(file_name):
    """Reads input file with input & output location of audio files.

    Args:
        file_name (str): Takes the full file path as input.

    Returns:
        A list of tuples. Tuple has (input_file_location, output_file_location)
    """
    with open(file_name, 'r') as input_file:
        output = [tuple(pair.split(","))
                    for pair in input_file.read().split("\n")
                    if pair != '']
    return output

def main():
    """Parses command line arguments passed to Alexa client script.
    """
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('-a', '--audio', action="store", default=None,
        help="takes .wav or .pcm file as audio input")
    parser.add_argument('-o', '--output', action="store", default=None,
        help=".mp3 file is returned from Alexa (if she returns audio)")
    parser.add_argument('-s', '--series', action="store",
        help="requires a command separated file with input file location")
    parser.add_argument('-m', '--multiple', action="store",
        help="requires a command separated file with input file location")
    parser.add_argument('-d', '--delay', action="store", type=int, default=0,
        help="delay between request in a series")
    args = parser.parse_args()

    alexa = AlexaClient()
    if args.audio:
        try:
            print alexa.ask(args.audio, args.output)
        except Exception as e:
            print e
            print "Audio sent:", args.audio
    elif args.series:
        inputs = read_input(args.series)
        print alexa.ask_series(inputs, delay=args.delay)
    elif args.multiple:
        inputs = read_input(args.multiple)
        print alexa.ask_multiple(inputs)


if __name__ == '__main__':
    main()
