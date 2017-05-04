# Alexa Client

Python client for Amazon's Alexa Voice Service (AVS).

## Prerequisites

### Amazon Developer Account

In order to use Alexa Voice Service you will need to signup for an Amazon Developer account. You can read about it on my [blog post](http://ewenchou.github.io/blog/2016/03/20/alexa-voice-service/) and get the details from [Amazon's Getting Started Guide](http://amzn.to/1Uui0QW).

In order to access Alexa Voice Service, you will also need to make an *Authorization Code Grant* request to get a refresh token. This is detailed in [Amazon's guide](https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/docs/authorizing-your-alexa-enabled-product-from-a-website).

See the **Authorization Code Grant** section below for an example of how to do this.

## Installation

1. Clone this repository

    ```
    git clone https://github.com/ewenchou/alexa-client.git
    ```

2. Configure settings. Set the `PRODUCT_ID`, `CLIENT_ID`,  `CLIENT_SECRET`, and `REFRESH_TOKEN` values in `alexa_client/settings.py`.

    *Note: If you do not have a refresh token, see the __Authorization Code Grant__ section below for an example of how to get one.*

3. Install requirements

    ```
    pip install -r requirements.txt
    ```

4. Install alexa_client

    ```
    python setup.py install
    ```

## Authorization Code Grant

The Python script, `auth_web.py` is included in this repository to make it easier to request an **Authorization Code Grant** as detailed in [Amazon's guide](https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/docs/authorizing-your-alexa-enabled-product-from-a-website).

**NOTE**: The `auth_web.py` script is taken and modified from the [respeaker/Alexa](https://github.com/respeaker/Alexa) Github repository.

You should have followed [Amazon's Getting Started Guide](http://amzn.to/1Uui0QW) and created a developer account as well as a new Alexa Voice Service device with a **Security Profile**.

You should now have the following values and they should be saved in `alexa_client/settings.py`:

* Device Type ID
* Client ID
* Client Secret

In order to authorize a client, you will also need to configure the **Web Settings** tab of the **Security Profile** of your device.

1. Log into the [Amazon Developer Portal](https://developer.amazon.com) and navigate to the Alexa Voice Service section. Click on the device you created in the list.
2. Click on **Security Profile** on the left menu.
3. Click on the **Web Settings** tab
4. Click on the **Edit** button and add the following:

    * Allowed Origins: `http://localhost:3000/`
    * Allowed Return URLs: `http://localhost:3000/authresponse`
5. Click the **Save** button to save the settings.

Install the requirements for `auth_web.py`:

        sudo pip install -r auth_web_requirements.txt

Now you can run the `auth_web.py` script.

1. Run the script: `python auth_web.py`
2. Open a web browser and go to `http://localhost:5000`
3. You should be redirected to an Amazon Login page. Enter your username and password and login.
4. You should now see a simple page that says `Success!` and the refresh token value.
5. Copy the refresh token value and set it in `alexa_client/settings.py`

## Run via command line

1. Make sure all installation steps are completed.
2. To see all command line options run: `python alexa_client/alexa_client.py -h`

```
optional arguments:
  -h, --help            show this help message and exit
  -a AUDIO, --audio AUDIO
                        takes .wav or .pcm file as audio input
  -o OUTPUT, --output OUTPUT
                        .mp3 file is returned from Alexa (if she returns audio)
  -s SERIES, --series SERIES
                        requires a comma separated file with input file location
  -m MULTIPLE, --multiple MULTIPLE
                        requires a comma separated file with input file location
  -d DELAY, --delay DELAY
                        delay between request in a series (seconds)
```

#### To send a single audio request to Alexa

`python alexa_client/alexa_client.py -a "/tmp/alexa_play_a_tribe_call_quest_radio_on_sonos.wav"`

To specify output file location:
`python alexa_client/alexa_client.py -a "/tmp/sample.wav" -o /tmp/out.mp3`

#### Send a list of audio requests in series (in order)

`python alexa_client/alexa_client.py -s audio_input.txt`

To add a delay:
`python alexa_client/alexa_client.py -s audio_input.txt -d 10`

**Note**: each line in the input file is formatted as such: **<input_file_location>,<output_file_location>**.
No quotes are needed in the file and the **<output_file_location>** is optional and can be left empty.
#### Send a list of audio requests concurrently

`python alexa_client/alexa_client.py -m audio_input.txt`

## Tests

Some sample tests are available in the `test` directory. Once installed and configured, you can run them to check if everything is working.

* Test a single request: `python test/test_ask.py`

* Test multiple concurrent requests: `python test/test_multiple.py`
