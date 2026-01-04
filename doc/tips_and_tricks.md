---
title: End of Speech Detection While Live Streaming
subtitle: >-
  Learn how to use End of Speech when transcribing live streaming audio with
  Deepgram.
slug: docs/understanding-end-of-speech-detection
---


To pinpoint the end of speech post-speaking more effectively, immediate notification of speech detection is preferred over relying on the initial transcribed word inference. This is achieved through a Voice Activity Detector (VAD), which gauges the tonal nuances of human speech and can better differentiate between silent and non-silent audio.

# Limitations of Endpointing

Deepgram's [Endpointing](/docs/endpointing) and [Interim Results](/docs/interim-results) features are designed to detect when a speaker finishes speaking.

Deepgram's Endpointing feature uses an audio-based Voice Activity Detector (VAD) to determine when a person is speaking and when there is silence. When the state of the audio goes from speech to a configurable duration of silence (set by the `endpointing` query parameter), Deepgram will chunk the audio and return a transcript with the `speech_final` flag set to `true`.

<Info>
  For more information, see [Understanding Endpointing and Interim Results When Transcribing Live Streaming Audio](/docs/understand-endpointing-interim-results)).
</Info>

In a quiet room with little background noise, Deepgram's Endpointing feature works well. In environments with significant background noise such as playing music, a ringing phone, or at a fast food drive thru, the background noise can cause the VAD to trigger and prevent the detection of silent audio. Since endpointing only fires after a certain amount of silence has been detected, a significant amount of background noise may prevent the `speech_final=true` flag from being sent.

<Info>
  In rare situations, such as when speaking a phone number, Deepgram may purposefully wait for additional audio from the speaker so it can properly format the transcript (this only occurs when using` smart_format=true`).
</Info>

## Using UtteranceEnd

To address the limitations described above, Deepgram offers the [UtteranceEnd](/docs/utterance-end) feature. The UtteranceEnd feature looks at the word timings of both finalized and interim results to determine if a sufficiently long gap in words has occurred. If it has, Deepgram will send a JSON message over the websocket with following shape:

<CodeGroup>
  ```json JSON
  {"type":"UtteranceEnd", "channel": [0,2], "last_word_end": 3.1}
  ```
</CodeGroup>

Your app can wait for this message to be sent over the websocket to identify when the speaker has stopped talking, even if significant background noise is present.

The `"channel"` field is interpreted as `[A,B]`, where `A` is the channel index, and `B` is the total number of channels. The above example is channel 0 of two-channel audio.

The `"last_word_end"` field is the end timestamp of the last word spoken before the utterance ended on the channel. This timestamp can be used to match against the earlier word-level transcript to identify which word was last spoken before the utterance end message was triggered.

To enable this feature, add the query parameter `utterance_end_ms=1234` to your websocket URL and replace `1234` with the number of milliseconds you want Deepgram to wait before sending the `UtteranceEnd` message.

For example, if you set `utterance_end_ms=1000` Deepgram will wait for a 1000 ms gaps between transcribed words before sending the `UtteranceEnd` message. Since this feature relies on word timings in the message transcript, it ignores non-speech audio such as: door knocking, a phone ringing or street noise.

You should set the value of `utterance_end_ms` to be `1000` ms or higher. Deepgram's Interim Results are sent every 1 second, so using a value of less than 1 second will not offer any benefits.

<Info>
  When using `utterance_end_ms`, setting `interim_results=true` is also required.
</Info>

## Using UtteranceEnd and Endpointing

You can use both the [Endpointing](/docs/endpointing) and [UtteranceEnd](/docs/utterance-end) features. They operate completely independently from one another, so it is possible to use both at the same time. When using both features in your app, you may want to trigger your "speaker has finished speaking" logic using the following rules:

* trigger when a transcript with `speech_final=true` is received (which may be followed by an `UtteranceEnd` message which can be ignored),
* trigger if you receive an `UtteranceEnd` message with no preceding `speech_final=true` message and send the last-received transcript for further processing.

## Additional Consideration

Ultimately, any approach to determine when someone has finished speaking is a heuristic one and may fail in rare situations. Since humans can resume talking at any time for any reason, detecting when a speaker has finished speaking or completed their thought is very difficult. To mitigate these concerns for your product, you may need to determine what constitutes "end of thought" or "end of speech" for your customers. For example, a voice-journaling app may need to allow for long pauses before processing the text, but a food ordering app may need to process the audio every few words.

***
---
title: Using Interim Results
subtitle: Learn how Interim Results can be useful for streaming audio.
slug: docs/using-interim-results
---


Deepgram’s Interim Results monitors streaming audio and provides interim transcripts, which are preliminary results provided during the real-time streaming process which can help with speech detection.

Below you will learn more about how to use interim results.

<Info>
  for information refer to the [Interim Results feature page.](/docs/interim-results)
</Info>

## Running The Example

[Download our final Python example script](https://res.cloudinary.com/deepgram/raw/upload/v1682358489/devex/show-final_e9za6a.py) and run the example code:

<CodeGroup>
  ```sh SHELL
  python3 show-final.py -k 'YOUR_DEEPGRAM_API_KEY' /PATH/TO/AUDIO.wav
  ```
</CodeGroup>

After execution, the script prints out the transcript for each response it receives and shows the `is_final` status for each message:

<CodeGroup>
  ```json JSON
  Channels = 2, Sample Rate = 48000 Hz, Sample width = 2 bytes, Size = 18540124 bytes
    1 0.000-1.100 ["is_final": false] another big
    2 0.000-2.100 ["is_final": false] another big problem
    3 0.000-3.100 ["is_final": false] another big problem in the speech analyst
    4 0.000-4.100 ["is_final": false] another big problem in the speech analytics space
    5 0.000-5.100 ["is_final": false] another big problem in the speech analytics space when custom
    6 0.000-6.100 ["is_final": false] another big problem in the speech analytics space when customers first bring the
    7 0.000-7.100 ["is_final": false] another big problem in the speech analytics space when customers first bring the software were on
    8 0.000-8.100 ["is_final": false] another big problem in the speech analytics space when customers first bring the software were on is that they
    9 0.000-9.100 ["is_final": false] another big problem in the speech analytics space when customers first bring the software on is that they they
   10 0.000-8.490 ["is_final": true ] another big problem in the speech analytics space when customers first bring the software were on is that they
   11 8.490-10.100 ["is_final": false] they are
   12 8.490-11.100 ["is_final": false] they are blown away by the
   ...
  ```
</CodeGroup>

In this response, we see that:

* On lines 1 through 9, the transcripts contain `"is_final": false`, indicating that they are interim transcripts. As more data passes to Deepgram, you see the transcripts is getting longer.
* Between lines 3 and 4, Deepgram corrects its prediction of the word "analyst," turning it into "analytics". This is an example of interim results in action.
* Between lines 5 and 6, Deepgram corrects its prediction of the word "custom", turning it into "customer". Another example of interim results in action.
* On line 10, `is_final` is set to `true`, indicating that Deepgram will not return any additional transcripts covering that span of time (from `0.000` to `8.490` seconds) because it believes it has reached optimal accuracy for this section of the transcript.
* On line 9, the transcript covers a span of time from `0.000` to `9.100` seconds, which is longer than the completed transcript issued on line 10. If you listen to this moment in the example audio, you will hear the speaker repeat the word "they". After processing the repeated word, Deepgram decided it had reached optimal accuracy for the first section of the transcript, and split the transcript between the repeated words. Notice one "they" stayed with the first section (line 10), but the other "they" moved into the next section (line 11), which starts at `8.490` seconds.

## Tips for working with transcripts

When handling real-time streaming results, the most accurate transcripts are available in the final transcripts, but the final transcripts may split the message.

* If you need the best transcript possible and can tolerate some delay, rely on final transcripts; they are most accurate and aren’t likely to change.

* If you need the fastest transcript possible, ignore final transcripts; instead, track timings and confidences to determine whether to keep waiting before committing to the current interim transcript. This usually works well because most content does not change between consecutive interim transcripts.

## Identify Completed Audio Processing

To identify whether the audio stream is completely processed, send an empty binary WebSocket message to the Deepgram server and then continue to process server responses until the server gracefully closes the connection.

## Frequently Asked Questions

### How do I measure latency with interim results?

In general terms, real-time streaming latency is the time delay between when a transfer of data begins and when a system begins processing it. In mathematical terms, it is the difference between the audio cursor (the number of seconds of audio you have currently submitted; we’ll call this X) and the latest transcript cursor (`start` + `duration`; we’ll call this Y). Latency is X-Y.

However, remember that to give you best accuracy, final transcripts may end early (see lines 9 and 10 in the example above), which means you’ve already received more data than what is reflected in the final transcript.

The final transcripts are meant for situations where you need the highest confidence levels, whereas the latest interim transcript has the lowest latency. It's recommended to always ignore final transcripts when calculating latency.

To learn more, see [Measuring Streaming Latency](/docs/measuring-streaming-latency).

### How do I measure word error rates (WER) with interim results?

To calculate [WER](https://blog.deepgram.com/what-is-word-error-rate/), concatenate all final transcripts and compare to your base transcript. Because final transcripts are the most accurate, they should be preferred over interim transcripts, which prioritize speed over accuracy. And because a single final transcript does not guarantee that the audio stream is complete, you will need to be certain you have collected all final transcripts before performing your calculation.

Let’s look at an example. [Download our WER Python example script](https://res.cloudinary.com/deepgram/raw/upload/v1682358520/devex/concat-final_p2jgsp.py), prepare an audio file (or [use our sample WAV file](https://res.cloudinary.com/deepgram/video/upload/v1681921235/devex/interview_speech-analytics_phntpw.wav)), and run the example code:

<CodeGroup>
  ```sh SHELL
  python3 concat-final.py -k 'YOUR_DEEPGRAM_API_KEY' /PATH/TO/audio.wav
  ```
</CodeGroup>

When run, the script concatenates the final transcripts returned by Deepgram and prints the result:

<CodeGroup>
  ```json JSON
  Channels = 2, Sample Rate = 48000 Hz, Sample width = 2 bytes, Size = 18540124 bytes
  another big problem in the speech analytics space when customers first bring the software where is that they they are blown away...
  ```
</CodeGroup>

You can compare this result with your base transcript to calculate WER.

***
---
title: Configure Endpointing and Interim Results
subtitle: Control when transcripts are returned during live streaming audio.
slug: docs/understand-endpointing-interim-results
---

This guide shows you how to configure [endpointing](/docs/endpointing/) and [interim results](/docs/interim-results/) to control transcript delivery timing in your streaming application.

## Configure endpointing for pause detection

Endpointing detects pauses in speech and returns `speech_final: true` when a pause is detected. Use this to trigger downstream processing when a speaker stops talking.

1. Set the `endpointing` parameter to a millisecond value in your WebSocket connection:

<CodeGroup>
```python Python
with client.listen.v1.connect(
    model="nova-3",
    language="en-US",
    endpointing=300  # 300ms of silence triggers speech_final
) as connection:
```
</CodeGroup>

2. Handle responses where `speech_final: true`:

<CodeGroup>
```json JSON
{
  "is_final": true,
  "speech_final": true,
  "channel": {
    "alternatives": [{
      "transcript": "another big"
    }]
  }
}
```
</CodeGroup>

**Recommended values:**

- **10ms (default):** Fast response for chatbots expecting short utterances
- **300-500ms:** Better for conversations where speakers pause mid-thought
- **`endpointing=false`:** Disable pause detection entirely

## Enable interim results for real-time feedback

Interim results provide preliminary transcripts as audio streams in, marked with `is_final: false`. When Deepgram reaches maximum accuracy for a segment, it sends a finalized transcript with `is_final: true`.

1. Set `interim_results=true` in your WebSocket connection:

<CodeGroup>
```python Python
with client.listen.v1.connect(
    model="nova-3",
    language="en-US",
    interim_results=True,
    endpointing=300
) as connection:
```
</CodeGroup>

2. Process responses based on the `is_final` flag:
   - `is_final: false` — Preliminary transcript, may change
   - `is_final: true` — Finalized transcript for this audio segment

## Combine both features for complete utterances

When using both features together, concatenate finalized transcripts to build complete utterances.

1. Enable both features in your WebSocket connection:

<CodeGroup>
```python Python
with client.listen.v1.connect(
    model="nova-3",
    language="en-US",
    interim_results=True,
    endpointing=300
) as connection:
```
</CodeGroup>

2. Append each `is_final: true` transcript to a buffer.

3. When `speech_final: true` arrives, the buffer contains the complete utterance.

4. Clear the buffer and start collecting the next utterance.

The following example shows how `is_final` and `speech_final` interact when a speaker dictates a credit card number:

<CodeGroup>
```json JSON
1 0.000-1.100 ["is_final": false] ["speech_final": false] yeah so
2 0.000-2.200 ["is_final": false] ["speech_final": false] yeah so my credit card number
3 0.000-3.200 ["is_final": false] ["speech_final": false] yeah so my credit card number is two two
4 0.000-4.300 ["is_final": false] ["speech_final": false] yeah so my credit card number is two two two two three
5 0.000-3.260 ["is_final": true ] ["speech_final": false] yeah so my credit card number is two two
6 3.260-5.100 ["is_final": false] ["speech_final": false] two two three three three three
7 3.260-5.500 ["is_final": true ] ["speech_final": true ] two two three three three three
```
</CodeGroup>

On line 5, `is_final: true` indicates a finalized transcript, but `speech_final: false` means the speaker hasn't paused yet. On line 7, both flags are `true`, signaling the end of an utterance. To get the complete transcript, concatenate lines 5 and 7.

<Warning>
Do not use `speech_final: true` alone to capture full transcripts. Long utterances may have multiple `is_final: true` responses before `speech_final: true` is returned.
</Warning>

## Implement utterance segmentation

For applications requiring complete sentences, add timing-based segmentation on top of endpointing.

1. Enable punctuation in your WebSocket connection:

<CodeGroup>
```python Python
with client.listen.v1.connect(
    model="nova-3",
    language="en-US",
    interim_results=True,
    endpointing=300,
    punctuate=True
) as connection:
```
</CodeGroup>

2. Process only `is_final: true` responses.

3. Break utterances at punctuation terminators or when the gap between adjacent words exceeds your threshold.

## Verify your configuration

Your configuration is working correctly when:

- Responses with `speech_final: true` arrive after detected pauses
- Interim results (`is_final: false`) update in real-time as audio streams
- Finalized transcripts (`is_final: true`) contain accurate text for each segment
- Complete utterances can be reconstructed by concatenating `is_final: true` responses until `speech_final: true`

## Next steps

- [Endpointing reference](/docs/endpointing/) — Full parameter documentation
- [Interim Results reference](/docs/interim-results/) — Detailed response format
- [Understanding End of Speech Detection](/docs/understanding-end-of-speech-detection) — Related speech detection features
---
title: Determining Your Audio Format for Live Streaming Audio
subtitle: >-
  Learn how to determine if your audio is containerized or raw, and what this
  means for correctly formatting your requests to Deepgram's API.
slug: docs/determining-your-audio-format-for-live-streaming-audio
---


Before you start streaming audio to Deepgram, it’s important that you understand whether your audio is containerized or raw, so you can correctly form your API request.

The difference between containerized and raw audio relates to how much information about the audio is included within the data:

* **Containerized audio stream:** A series of bits is passed along with a header that specifies information about the audio. Containerized audio generally includes enough additional information to allow Deepgram to decode it automatically.
* **Raw audio stream:** The series of bits is passed with no further information. Deepgram needs you to manually provide information about the characteristics of raw audio.

## Streaming Raw Audio

If you’re streaming raw audio to Deepgram, you must provide the [encoding](/docs/encoding/) and [sample rate](/docs/sample-rate/) of your audio stream in your request. Otherwise, Deepgram will be unable to decode the audio and will fail to return a transcript.

An example of a Deepgram API request to stream raw audio:

```
wss://api.deepgram.com/v1/listen?encoding=ENCODING_VALUE&sample_rate=SAMPLE_RATE_VALUE
```

<Info>
  To see a list of raw audio encodings that Deepgram supports, [check out our Encoding documentation](/docs/encoding/).
</Info>

## Streaming Containerized Audio

If you’re streaming containerized audio to Deepgram, you should not set the encoding and sample rate of your audio stream. Instead, Deepgram will read the container’s header and get the correct information for your stream automatically.

An example of a Deepgram API request to stream containerized audio:

```
wss://api.deepgram.com/v1/listen
```

<Info>
  Deepgram supports over 100 different audio formats and encodings. You can see some of the most popular ones at [Supported Audio Format](/docs/supported-audio-formats).
</Info>

## Determining Your Audio Format

If you’re not sure whether your audio is raw or containerized, you can identify audio format in a few different ways.

### Check Documentation

Start by checking any available documentation for your audio source. Often, it will provide details related to audio format. Specifically, check for any mentions of encodings like Opus, Vorbis, PCM, mu-law, A-law, s16, or linear16.

If your audio source is a web API stream, in many cases it will already be containerized. For example, the audio may be raw Opus audio wrapped in an Ogg container or raw PCM audio wrapped in a WAV container.

### Automatically Detect Audio Format

If you’re still not sure whether or not your audio is containerized, you can write an audio stream to disk and try listening to it with a program like VLC. If your audio is containerized, VLC will be able to play it back without any additional configuration.

Alternatively, you can use `ffprobe` (part of the ffmpeg package, which is a cross-platform solution that records, converts, and streams audio and video) to gather information from the audio stream and detect the audio format of a file.

To use `ffprobe`, from a terminal, run:

<CodeGroup>
  ```shell Shell
  ffprobe PATH_TO_FILE
  ```
</CodeGroup>

The last line of the output from this command will include any data `ffprobe` is able to determine about the file’s audio format.

## Using Raw Audio with Encoding & Sample Rate

When using raw audio, make sure to set the [encoding](/docs/encoding/) and the [sample rate](/docs/sample-rate/). Both parameters are required for Deepgram to be able to decode your stream.

***
---
title: Measuring Streaming Latency
subtitle: Learn how to measure latency in real-time streaming of audio using Deepgram.
slug: docs/measuring-streaming-latency
---


In general terms, real-time streaming latency is the time delay between when a transfer of data begins and when a system begins processing it.

In mathematical terms, it is the difference between the audio cursor (the number of seconds of audio you have currently submitted; we’ll call this X) and the latest transcript cursor (`start` + `duration`; we’ll call this Y). Latency is X-Y.

## Causes of Latency

Causes of latency include:

* **Network/transmission latency**: Physical distance and network infrastructure can add significant delays to your messages (both to and from Deepgram).
* **Network stack**: How long it takes a message to be routed through the operating system and network driver to the network card itself. When an application wants to send a message to another machine, this must happen, and it can be influenced by numerous factors, including computer load, firewalls, and network traffic. Similarly, the receiving machine’s network card must push the message up through the operating system and into the receiving application.
* **Serialization/deserialization**: How long it takes to interpret a message and convert it into a usable form. To send or receive a message, your client must do this, just as Deepgram's servers must.
* **Transcription latency**: How long it takes to process audio. As powerful as they are, Deepgram's servers still require time to process audio and convert it into usable analytics and transcription results.
* **Buffer size**: The amount of audio sent in each streaming message. Too large of a buffer adds built-in delay to getting results while the audio buffers. Too small of a buffer adds a lot of tiny packets, degrading network performance. Streaming buffer sizes should be between 20 milliseconds and 250 milliseconds of audio, with 100 milliseconds often striking a good balance.

Typically, transcription latency is the largest contributor, but non-transcription latencies often compose 10-30% of total latency costs, which is significant when you need immediate transcripts.

## Measuring Non-transcription Latency

Measuring non-transcription latency is a complicated process that relies heavily on your testing computer, its current load, the client-side programming language, network configuration, and physical location. The most traditional tool of the trade is `ping`, which sends a special message to a remote server asking it to `echo` back.

For security purposes, Deepgram blocks pings; instead, for a more realistic measurement, you can measure the time it takes to connect to Deepgram's servers:

<CodeGroup>
  ```bash cURL
  curl -sSf -w "latency: %{time_connect}\n" -so /dev/null https://api.deepgram.com
  # latency: {number in decimal seconds}
  ```
</CodeGroup>

In this example, we see that it takes `111` milliseconds to establish a TCP connection to Deepgram.

## Measuring Transcription Latency

Transcription latency cannot be measured directly. To calculate transcription latency, you must first calculate total latency and then subtract non-transcription latency.

### Calculating Total Latency

To calculate total latency:

1. **Measure amount of audio submitted**. Track the number of seconds of audio you’ve submitted to Deepgram. This represents the audio cursor; we’ll call this X.
2. **Measure the amount of audio processed**. Every time you receive an interim transcript (i.e., containing `"is_final": false`) from Deepgram, record the `start` + `duration` value. This is the transcript cursor; we’ll call this Y.
3. **Find total latency**: Subtract Y from X to calculate total latency (X-Y).

<Info>
  To learn more about why you should only include interim transcripts in this calculation, see [Understand Interim Transcripts: How do I measure latency with interim results?](/docs/using-interim-results#how-do-i-measure-latency-with-interim-results).
</Info>

### Calculating Transcription Latency

To calculate transcription latency, subtract non-transcription latency from total latency:

Transcription Latency = Total Latency - Non-Transcription Latency

Let’s look at an example. [Download our latency Python example script](https://res.cloudinary.com/deepgram/raw/upload/v1681940340/devex/latency_zetbdo.py), prepare an audio file (or [use our sample WAV file](https://res.cloudinary.com/deepgram/video/upload/v1681921235/devex/interview_speech-analytics_phntpw.wav)), and run the example code. (If you're measuring latency for a self-hosted Deepgram deployment, you'll need to edit the API endpoint on line 43 to point to your installation's URL.)

<CodeGroup>
  ```shell Shell
  python3 latency.py -k 'YOUR_DEEPGRAM_API_KEY' /PATH/TO/AUDIO.wav
  ```
</CodeGroup>

When run, the script submits the identified audio file to Deepgram in real time and prints the total latency to the screen:

<CodeGroup>
  ```json JSON
  Channels = 2, Sample Rate = 48000 Hz, Sample width = 2 bytes, Size = 18540124 bytes
  Measuring... Audio cursor = 2.580, Transcript cursor = 0.220
  Measuring... Audio cursor = 2.580, Transcript cursor = 0.420
  Measuring... Audio cursor = 2.580, Transcript cursor = 0.620
  Measuring... Audio cursor = 2.580, Transcript cursor = 0.840
  ...
  Min latency: 0.080
  Avg latency: 0.674
  Max latency: 1.180
  ```
</CodeGroup>

In this example, total latency averages `674` milliseconds, while previously we measured non-transcription latency at approximately `111` milliseconds. So in this example, transcription latency is `674`-`111`=`563` ms.

***
---
title: 'STT Troubleshooting WebSocket, NET, and DATA Errors'
subtitle: 'Learn how to debug common real-time, live streaming transcription errors.'
slug: docs/stt-troubleshooting-websocket-data-and-net-errors
---

When working with Deepgram's Speech To Text Streaming API, you may encounter WebSocket errors. This troubleshooting guide helps you quickly identify and resolve the most common issues.

## WebSocket Basics

- WebSocket enables two-way, real-time communication between client and server.
- The connection is established via an HTTP handshake and upgraded to WebSocket.
- If the handshake fails, you'll get an HTTP `4xx` or `5xx` error.
- The connection stays open until closed by either side.

### Establishing a WebSocket Connection

- The client initiates a WebSocket connection with an HTTP handshake, optionally including query parameters or headers (for authentication, etc.).
- Most libraries handle the handshake automatically (e.g., `websockets.connect`).
- If successful, the server responds with HTTP `101` and upgrades the connection.
- If unsuccessful, you'll receive an HTTP `4xx` or `5xx` error and the connection won't be established.

### Closing the WebSocket Connection

- A successfully opened WebSocket connection will stay alive until it is eventually closed by either the client or the server. When this occurs, a [WebSocket Close Frame](https://tools.ietf.org/html/rfc6455#section-5.5.1) will be returned.
- The body of the Close frame will indicate the reason for closing with a [pre-defined status code](https://tools.ietf.org/html/rfc6455#section-7.4.1) followed by a UTF-8-encoded payload that represents the reason for the error.
- To close the WebSocket connection from your client, send a [Close Stream](/docs/close-stream) message. The server will then finish processing any remaining data, send a final response and summary metadata, and terminate the connection.
- After sending a Close message, the endpoint considers the WebSocket connection closed and will close the underlying TCP connection.

<Warning>
  Sending an empty byte (e.g., `b''`) will cause unexpected closures. Avoid sending an empty byte accidentally by adding a conditional to check if the length of your audio packet is 0 before sending.
</Warning>

## Using KeepAlive Messages to Prevent Timeouts

- Send a [KeepAlive](/docs/audio-keep-alive) message periodically to keep the connection open.
- Doing this can prevent timeouts and NET-0001 errors (no audio received for 10 seconds).

## Common WebSocket Errors

### Failure to Connect

If a failure to connect occurs, Deepgram returns custom HTTP headers for debugging:
  - `dg-request-id`: Always present, contains the request ID.
  - `dg-error`: Present on failed upgrades, contains the error message.

<Info>
  Access to these headers will depend on the WebSocket library you are using. For example, browser-based WebSocket libraries like the JavaScript WebSocket library only allow access to HTTP header information for successful WebSocket connections.
</Info>

### Debugging Connection Failures

If you're unable to connect the Deepgram API provides custom HTTP headers that contain debugging information:

* Regardless of the success or failure of the WebSocket upgrade, all requests include the `dg-request-id` HTTP header, which contains the request ID.
* Requests that do not successfully upgrade to a WebSocket connection also include the `dg-error` HTTP header, which contains a detailed error message concerning why the connection could not be upgraded. This error message is also sent back in the body of the HTTP response.


### Code Samples

These code samples demonstrate how to connect to Deepgram’s API using WebSockets, authenticate with your API key, and handle both successful and failed connection attempts by printing relevant request IDs and error messages for troubleshooting.

<Warning>
  Replace `YOUR_DEEPGRAM_API_KEY` with your [Deepgram API Key](/docs/create-additional-api-keys).
</Warning>

<CodeGroup>
  ```python Python
  import websockets
  import json
  import asyncio

  async def main():
      try:
          async with websockets.connect('wss://api.deepgram.com/v1/listen',
          # Remember to replace the YOUR_DEEPGRAM_API_KEY placeholder with your Deepgram API Key
          extra_headers = { 'Authorization': f'token YOUR_DEEPGRAM_API_KEY' }) as ws:
              # If the request is successful, print the request ID from the HTTP header
              print('🟢 Successfully opened connection')
              print(f'Request ID: {ws.response_headers["dg-request-id"]}')
              await ws.send(json.dumps({
                  'type': 'CloseStream'
              }))
      except websockets.exceptions.InvalidStatusCode as e:
          # If the request fails, print both the error message and the request ID from the HTTP headers
          print(f'🔴 ERROR: Could not connect to Deepgram! {e.headers.get("dg-error")}')
          print(f'🔴 Please contact Deepgram Support with request ID {e.headers.get("dg-request-id")}')

  asyncio.run(main())
  ```

  ```javascript JavaScript
  const WebSocket = require('ws');
  const ws = new WebSocket('wss://api.deepgram.com/v1/listen', {
      headers: {
        // Remember to replace the YOUR_DEEPGRAM_API_KEY placeholder with your Deepgram API Key
        Authorization: 'Token YOUR_DEEPGRAM_API_KEY',
      },
  });
  // For security reasons, browser-based WebSocket libraries only allow access to HTTP header information for successful WebSocket connections
  // If the request is successful, return the HTTP header that contains the request ID
  ws.on('upgrade', function message(data) {
      console.log(data.headers['dg-request-id']);
  });
  ```
</CodeGroup>

### Abrupt WebSocket Closures

If Deepgram encounters an error during real-time streaming, the Deepgram API returns a [WebSocket Close frame](https://www.rfc-editor.org/rfc/rfc6455#section-5.5.1). The body of the Close frame will indicate the reason for closing with a [pre-defined status code](https://tools.ietf.org/html/rfc6455#section-7.4.1) followed by a UTF-8-encoded payload that represents the reason for the error.

Below are the most common WebSocket Close frame status codes and their descriptions.


| Code   | Payload     | Description                                                                                                                                                                                                                   |
| ------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `1008` | `DATA-0000` | The payload cannot be decoded as audio. The payload either is not audio data or is a codec unsupported by Deepgram.                                                                                                           |
| `1011` | `NET-0000`  | The service has not transmitted a Text frame to the client within the timeout window. This may indicate an internal issue with Deepgram's systems, or Deepgram may have not received enough audio data to transcribe a frame. |
| `1011` | `NET-0001`  | The service has not received a Binary or Text frame from the client within the timeout window. This may indicate an internal issue with Deepgram's systems, the client's systems, or the network connecting them.             |

#### Troubleshooting `1008` - `DATA-0000`

- Check the data being sent is valid audio.
- Check the audio data is not empty.
- If the audio data is valid, check whether the audio being sent is raw or containerized.
- Write the audio data to a file to make sure it contains the expected audio and can be played back.
- Ensure [Encoding](/docs/encoding) and [Sample Rate](/docs/sample-rate) parameters are set correctly.
- See [Audio Format For Live Streaming](/docs/determining-your-audio-format-for-live-streaming-audio) for more information.


#### Troubleshooting `1011` - `NET-0000`
- This indicates an internal server error.
- Retry your request.
- Check [Deepgram status](https://status.deepgram.com/) to see if there are any ongoing issues.
- If Deepgram is operational, [contact Support](/support) for assistance.

#### Troubleshooting `1011` - `NET-0001`

- Ensure audio is sent within 10 seconds of opening the connection.
- You can send silent audio to keep the connection alive.
- Using `KeepAlive` messages alone will not prevent closure; you must send at least one audio message.
- Be sure to send a [Close Stream](/docs/close-stream) message when done.
- Test your network with cURL and Deepgram-hosted audio. See [Generating Transcripts from the Terminal](/docs/generating-and-saving-transcripts-from-the-terminal) for more information.
- Use a tool like [Wireshark](https://www.wireshark.org/) to confirm audio is leaving your network.

***
---
title: Recovering From Connection Errors & Timeouts When Live Streaming
subtitle: >-
  Learn how to implement real-time, live streaming transcription solutions for
  long-running audio streams.
slug: docs/recovering-from-connection-errors-and-timeouts-when-live-streaming-audio
---


Deepgram's API allows you to live stream audio for real-time transcription. Our live streaming service can be used with WebSocket streams. The longer a WebSocket stream persists, the more chances there are for transient network or service issues to cause a break in the connection. We recommend that you be prepared to gracefully recover from streaming errors, especially if you plan to live-stream audio for long periods of time (for example, if you are getting live transcription of a day-long virtual conference).

Implementing solutions that correctly handle disrupted connections can be challenging. In this guide, we recommend some solutions to the most common issues developers face when implementing real-time transcription with long-running live audio streams.

## Before You Begin

Before you begin, make sure you:

* have basic familiarity with Deepgram's API, specifically its [Transcribe Streaming Audio endpoint](/reference/speech-to-text/listen-streaming).
* understand how to make WebSocket requests and receive API responses.

## Main Issues

When you use Deepgram's API for real-time transcription with long-running live audio streams, you should be aware of some challenges you could encounter.

### Disrupted Connections

While Deepgram makes every effort to preserve streams, it's always possible that the connection could be disrupted. This may be due to internal factors or external ones, including bandwidth limitations and network failures.

In these cases, your application must initialize a new WebSocket connection and start a new streaming session. Once the new WebSocket connection is accepted and you receive the message indicating the connection is open, your application can begin streaming audio to it. You must stream audio to the new connection within 10 seconds of opening, or the connection will close due to lack of data.

## Data Loss

If you must reconnect to the Deepgram API for any reason, you could encounter loss of data while you are reconnecting since audio data will still be produced, but will not be transferred to our API during this period.

To avoid losing the produced audio while you are recovering the connection, you should have a strategy in place. We recommend that your application stores the audio data in a buffer until it can re-establish the connection to our API and then sends the data for delayed transcription. Because Deepgram allows audio to be streamed at a maximum of 1.25x realtime, if you send a large buffer of audio, the stream may wind up being significantly delayed.

## Corrupt Timestamps

Deepgram returns transcripts that include timestamps for every transcribed word. Timestamps correspond to the moments when the words are spoken within the audio. Every time you reconnect to our API, you create a new connection, so the timestamps on your audio begin from 00:00:00 again.

Because of this, when you restart an interrupted streaming session, you'll need to be sure to realign the timestamps to the audio stream. We recommend that your application maintains a starting timestamp to offset all returned timestamps. When you process a timestamp returned from Deepgram, add your maintained starting timestamp to the returned timestamp to ensure that it is offset by the correct amount of time.

***
---
title: Using Lower-Level Websockets with the Streaming API
subtitle: >-
  Learn how to implement using lower-level websockets with Deepgram's Streaming
  API.
slug: docs/lower-level-websockets
---


The [Deepgram's Streaming API](/reference/speech-to-text/listen-streaming) unlocks many use cases ranging from captioning to notetaking and much more. If you aren't able to use our Deepgram SDKs for your Streaming needs, this guide will provide a Reference Implementation for you.

<Info>
  Most users will not need this Reference Implementation because Deepgram provides [SDKs](/home) that already implement the Streaming API. This is an **optional** guide to help individuals interested in building and maintaining their own SDK specific to the Deepgram Streaming API.
</Info>

For additional reference see our Deepgram SDKs which include the Websocket-based Streaming API:

* [Javascript SDK](/home)
* [Python SDK](/home)
* [.NET SDK](/home)
* [Go SDK](/home)

## Using a Deepgram SDK vs Building Your Own SDK

The Deepgram SDKs should address most needs; however, if you find limitations or issues in any of the above SDKs, we encourage you to report issues, bugs, or ideas for new features in the open source repositories. Our SDK projects are open to code contributions as well.

If you still need to implement your own SDK, this guide will enable you to do that.

## Prerequisites

It is highly recommended that you familiarize yourself with the WebSocket protocol defined by [RFC-6455](https://datatracker.ietf.org/doc/html/rfc6455). If you are still getting familiar with what an [IETF RFC](https://www.ietf.org/standards/rfcs/) is, they are very detailed specifications on how something works and behaves. In this case, [RFC-6455](https://datatracker.ietf.org/doc/html/rfc6455) describes how to implement WebSockets. You will need to understand this document to understand how to interact with the Deepgram Streaming API.

Once you understand the WebSocket protocol, it's recommended to understand the capabilities of your WebSocket protocol library available in the language you chose to implement your SDK in.

Refer to the language specific implementations for [RFC-6455](https://datatracker.ietf.org/doc/html/rfc6455) (i.e. the WebSocket protocol):

* [JavaScript](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
* [Python](https://github.com/python-websockets/websockets)
* [GOrilla](https://github.com/gorilla/websocket) or [Go Networking](https://cs.opensource.google/go/x/net)
* [C# .NET](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/websockets?view=aspnetcore-8.0)

These are just some of the available implementations in those languages. They are just the ones that are very popular in those language-specific communities.

Additionally, you will need to understand applications that are [multi-threaded](https://en.wikipedia.org/wiki/Multithreading_\(computer_architecture\)), [access the internet](https://en.wikipedia.org/wiki/Computer_network_programming), and do so [securely via TLS](https://en.wikipedia.org/wiki/Secure_Sockets_Layer). These are going to be essential components to building your SDK.

## Deepgram Streaming API

The goal of your SDK should minimally be:

* **Manage the Connection Lifecycle**: Implement robust connection management to handle opening, error handling, message sending, receiving, and closing of the WebSocket connection.
* **Concurrency and Threading**: Depending on the SDK's target language, manage concurrency appropriately to handle the asynchronous nature of WebSocket communication without blocking the main thread.
* **Error Handling and Reconnection**: Implement error handling and automatic reconnection logic. Transient network issues should not result in lost data or service interruptions.
* **Implement KeepAlives**: Deepgram's API may require keepalive messages to maintain the connection. Implement a mechanism to send periodic pings or other suitable messages to prevent timeouts.

## High-Level Pseudo-Code for Deepgram Streaming API

It's essential that you encapsulate your WebSocket connection in a class or similar representation. This will reduce undesired, highly coupled WebSocket code with your application's code. In the industry, this has often been referred to as minimizing ["Spaghetti code"](https://en.wikipedia.org/wiki/Spaghetti_code). If you have WebSocket code or you need to import the above WebSocket libraries into your `func main()`, this is undesirable unless your application is trivially small.

To implement the WebSocket Client correctly, you must implement based on the WebSocket protocol defined in [RFC-6455](https://datatracker.ietf.org/doc/html/rfc6455). Please refer to section [4.1 Client Requirements](https://datatracker.ietf.org/doc/html/rfc6455#section-4.1) in RFC-6455.

You want first to declare a WebSocket class of some sort specific to your implementation language:

<CodeGroup>
  ```text Text
  // This class could simply be called WebSocketClient
  // However, since this is specifically for Deepgram, it could be called DeepgramClient
  class WebSocketClient {
    private url: String
    private apiKey: String
    private websocket: WebSocket
    
    // other class properties
    
    // other class methods
  }
  ```
</CodeGroup>

**NOTE:** Depending on the programming language of choice, you might either need to implement `async`/`await` and `threaded` classes to support both threading models. These concepts occur in languages like Javascript, Python, and others. You can implement one or both based on your user's needs.

You will then need to implement the following class methods.

### Function: Connect

```
class WebSocketClient {
  ...
  function Connect() {
    // Implement the websocket connection here 
  }
  ...
}
```

This function should:

* Initialize the WebSocket connection using the `URL` and `API Key`.
* Set up event listener threads for connection events (message, metadata, error).
* Start the keep alive timer based on the `Keepalive Interval`.

### Thread: Receive and Process Messages

```
class WebSocketClient {
  ...
  function ThreadProcessMessages() {
    // Implement the thread handler to process messages
  }
  ...
}
```

This thread should:

* When a message arrives, check if it's a transcription result or a system message.
* For transcription messages, process or handle the transcription data.
* Handle system messages accordingly (may include error messages or status updates).

### Function: Send

```
class WebSocketClient {
  ...
  function SendBinary([]bytes) {
    // Implements a send function to transport audio to the Deepgram server
  }

  function SendMessage([]byte) {
    // Implements a send function to transport control messages to the Deepgram server 
  }
  ...
}
```

The `SendBinary()` function should:

* Accept audio data as input.
* Send the audio data over the WebSocket connection to Deepgram for processing.

The `SendMessage()` function should:

* Accept JSON data as input.
* Send the JSON over the WebSocket connection to Deepgram for handling control or connection management type functions. A `KeepAlive` or `CloseStream` messages are examples of these types of messages.

If you need more information on the difference, please refer to [RFC-6455](https://datatracker.ietf.org/doc/html/rfc6455).

### (Optional) Thread: KeepAlive

```
class WebSocketClient {
  ...
  function ThreadKeepAlive() {
    // Implement the thread handler to process messages
  }
  ...
}
```

This thread is optional providing that audio data is constantly streaming to through the WebSocket; otherwise, it should:

* Regularly send a keepalive message (such as a ping) to Deepgram based on the `Keepalive Interval` to maintain the connection.

Notice this thread is independent of the Receive/Process Message Thread above.

### Function: Close

```
class WebSocketClient {
  ...
  function Close() {
    // Implement shutting down the websocket
  }
  ...
}
```

This function should:

* Send a command to close the WebSocket connection.
* Stop the keepalive timer to clean up resources.

## Deepgram API Specifics

Now that you have a basic client, you must handle the Deepgram API specifics. Refer to this documentation for[ more information](/reference/speech-to-text/listen-streaming) .

### Function: Connect

When establishing a connection, you must pass the required parameters defined by the [Deepgram Query Parameters](/reference/speech-to-text/listen-streaming#query-params).

### Thread: Receive and Process Messages

If successfully connected, you should start receiving transcription messages (albeit empty) in the [Response Schema](/reference/speech-to-text/listen-streaming#response-schema) defined below.

<CodeGroup>
  ```json JSON
  {
    "metadata": {
      "transaction_key": "string",
      "request_id": "uuid",
      "sha256": "string",
      "created": "string",
      "duration": 0,
      "channels": 0,
      "models": [
        "string"
      ],
    },
    "type": "Results",
    "channel_index": [
      0,
      0
    ],
    "duration": 0.0,
    "start": 0.0,
    "is_final": boolean,
    "speech_final": boolean,
    "channel": {
      "alternatives": [
        {
          "transcript": "string",
          "confidence": 0,
          "words": [
            {
              "word": "string",
              "start": 0,
              "end": 0,
              "confidence": 0
            }
          ]
        }
      ],
      "search": [
        {
          "query": "string",
          "hits": [
            {
              "confidence": 0,
              "start": 0,
              "end": 0,
              "snippet": "string"
            }
          ]
        }
      ]
    }
  }
  ```
</CodeGroup>

For convenience, you will need to marshal these JSON representations into usable objects/classes to give your users an easier time using your SDK.

### (Optional) Thread: KeepAlive

If you do implement the KeepAlive message, you will need to follow the [guidelines defined here.](/reference/speech-to-text/listen-streaming#stream-keepalive)

### Function: Close

When you are ready to close your WebSocket client, you will need to follow the shutdown [guidelines defined here.](/reference/speech-to-text/listen-streaming#close-stream)

### Special Considerations: Errors

You must be able to handle any protocol-level defined in [RFC-6455](https://datatracker.ietf.org/doc/html/rfc6455) and application-level (i.e., messages from Deepgram) you will need to follow the [guidelines defined here.](/reference/speech-to-text/listen-streaming#error-handling)

## Troubleshooting

Here are some common implementation mistakes.

### My WebSocket Connection Immediately Disconnects

There are usually a few reasons why the Deepgram Platform will terminate the connection:

* No audio data is making it through the WebSocket to the Deepgram Platform. The platform will terminate the connection if no audio data is received in roughly 10 seconds.
* A variation on the above... you have muted the audio source and are no longer sending an audio stream or data.
* The audio encoding is not supported OR the [`encoding`](/docs/encoding) parameter does not match the encoding in the audio stream.
* Invalid connection options via the query parameters are being used. This could be things like misspelling an option or using an incorrect value.

### My WebSocket Connection Disconnects in the Middle of My Conversation

There are usually a few reasons why the Deepgram Platform will terminate the connection (similar to the above):

* You have muted the audio source and are no longer sending an audio stream or data.
* If no audio data is being sent, you must implement the [KeepAlive](/reference/speech-to-text/listen-streaming#stream-keepalive) protocol message.

### My Transcription Messages Are Getting Delayed

There are usually a few reasons why the Deepgram Platform delays sending transcription messages:

* You inadvertently send the [KeepAlive](/reference/speech-to-text/listen-streaming#stream-keepalive) protocol message as a Data or Stream message. This will cause the audio processing to choke or hiccup, thus causing the delay. Please refer to [RFC-6455](https://datatracker.ietf.org/doc/html/rfc6455) to learn more about the difference between data and control messages.
* Network connectivity issues. Please ensure your connection to the Deepgram domain/IP is good. Use `ping` and `traceroute` or `tracert` to map the network path from source to destination.

## Additional Considerations

By adopting object-oriented programming (OOP), the pseudo-code above provides a clear structure for implementing the SDK across different programming languages that support OOP paradigms. This structure facilitates better abstraction, encapsulation, and modularity, making the SDK more adaptable to future changes in the Deepgram API or the underlying WebSocket protocol.

As you implement and refine your SDK, remember that the essence of good software design lies in solving the problem at hand and crafting a solution that's maintainable, extensible, and easy to use.

***
