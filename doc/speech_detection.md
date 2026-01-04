---
title: Speech Started
subtitle: >-
  Speech Started sends a message when the start of speech is detected in live
  streaming audio.
slug: docs/speech-started
---


`vad_events` *boolean*.

<div class="flex flex-row gap-2">
  <span class="dg-badge unavailable strike-through"><span><Icon icon="file" /> Pre-recorded</span></span>
   <span class="dg-badge"><span><Icon icon="waveform-lines" /> Streaming:Nova</span></span> <span class="dg-badge pink"><span><Icon icon="language" /> All available languages</span></span>
 
</div>

Deepgram's Speech Started feature can be used for speech detection and can be used to detect the start of speech while transcribing live streaming audio.

SpeechStarted complements Voice Activity Detection (VAD) to promptly detect the start of speech post-silence. By gauging tonal nuances in human speech, the VAD can effectively differentiate between silent and non-silent audio segments, providing immediate notification of speech detection.

## Enable Feature

To enable the SpeechStarted event, include the parameter `vad_events=true` in your request:

`vad_events=true`

You'll then begin receiving messages upon speech starting.

<CodeGroup>
  ```python Python

  # For help migrating to the new Python SDK, check out our migration guide:
  # https://github.com/deepgram/deepgram-python-sdk/blob/main/docs/Migrating-v3-to-v5.md

     with client.listen.v1.connect(
              model="nova-3",
              language="en-US",
              # Apply smart formatting to the output
              smart_format=True,
              # Raw audio format details
              encoding="linear16",
              channels=1,
              sample_rate=16000,
              # To get UtteranceEnd, the following must be set:
              interim_results=True,
              utterance_end_ms="1000",
              vad_events=True,
              # Time in milliseconds of silence to wait for before finalizing speech
              endpointing=300
     ) as connection:
  ```
</CodeGroup>

## Results

The JSON message sent when the start of speech is detected looks similar to this:

<CodeGroup>
  ```json JSON
  {
    "type": "SpeechStarted",
    "channel": [
      0,
      1
    ],
    "timestamp": 9.54
  }
  ```
</CodeGroup>

* The `type` field is always `SpeechStarted` for this event.
* The `channel` field is interpreted as `[A,B]`, where `A` is the channel index, and `B` is the total number of channels. The above example is channel 0 of single-channel audio.
* The `timestamp` field is the time at which speech was first detected.

<Warning>
  The timestamp doesn't always match the start time of the first word in the next transcript because the systems for transcribing and timing words work independently of the speech detection system.
</Warning>

***
---
title: Utterance End
subtitle: >-
  Utterance End sends a message when the end of speech is detected in live
  streaming audio.
slug: docs/utterance-end
---

`utterance_end_ms` *string*

<div class="flex flex-row gap-2">
<span class="dg-badge unavailable strike-through"><span><Icon icon="file" /> Pre-recorded</span></span>
 <span class="dg-badge"><span><Icon icon="waveform-lines" /> Streaming:Nova</span></span> <span class="dg-badge pink"><span><Icon icon="language" /> All available languages</span></span>
 
</div>

The utterance end feature can be used for speech detection and can be enabled to help detect the end of speech while transcribing live streaming audio.

Utterance end analyzes your interim and final results to identify a gap of the configured length after the last finalized word. The feature operates by analyzing interim and final transcripts to detect a sufficient silence gap following the last finalized word, requiring interim results to identify gaps that meet the configured duration. Utterance end provides a convenient server-side implementation of gap detection that could alternatively be implemented client-side by analyzing the timing of transcription results, allowing developers to choose the approach that best fits their application architecture.

## Enable Feature

To enable this feature, add `utterance_end_ms=1000` to your request. Replace `1000` with the number of milliseconds you want Deepgram to wait before sending the UtteranceEnd message. Utterance end analyzes your interim and final results to detect when there is a gap of the configured length after the last finalized word, then sends the UtteranceEnd message.

For example, if you set `utterance_end_ms=1000`, Deepgram will wait for a 1000 millisecond gap between transcribed words before sending the UtteranceEnd message.

### How It Works: A Concrete Example

Here's how utterance end works with interim and finalized results:

1. **Speaker says:** "Hello there" (pauses for 1.5 seconds) "How are you?"
2. **With `utterance_end_ms=1000`:**
   - **0.5s:** Interim result: `"Hello"`
   - **1.0s:** Interim result: `"Hello there"`  
   - **2.0s:** Final result: `"Hello there"` with word timings:
     - "Hello": start=0.1s, end=0.6s
     - "there": start=0.7s, end=1.2s
   - **🕒 Utterance end clock starts:** At 1.2s (end time of last finalized word "there")
   - **2.2s:** 1000ms gap reached → **UtteranceEnd message sent** (`last_word_end=1.2`)
   - **3.5s:** New speech detected, interim result: `"How are you?"`

The utterance end "clock" only starts counting after receiving the end timestamp of the last finalized word, ensuring accurate gap detection.

## Technical Notes

While utterance end provides convenient server-side gap detection, there are some technical considerations to keep in mind:

### Gap Detection Within Final Results
Utterance end only analyzes gaps that occur after finalized words. It does not detect gaps that are contained entirely within a single final result. This design extends beyond just internal word gaps: if a final result's last word ends at 7.5 seconds but the result itself doesn't end until 10.0 seconds, utterance end will wait for an additional interim result before considering the gap—because the entire gap is contained within that single final result.

This means you could potentially get faster gap detection by implementing client-side analysis that includes gaps within final transcripts.

For example, if a final result contains "Hello... there" with a 2-second pause represented in the word timings, utterance end would not fire based on that internal gap—it only analyzes gaps that occur after the final result is processed.

### Voice Agent Use Case Considerations
Utterance end fires based on detecting a gap even if it determines that speech is continuing after the gap. This can make it less ideal for voice agent applications where you want to wait for truly complete utterances.

**Example with `utterance_end_ms=2000`:**
```
[Interim] Hello there. This
[Interim] Hello there. This is a test.
[Final] Hello there. This is a test. (last_word_end = 3.4s)
[Interim] (result_end = 4.7s)
[Interim] I'm going to continue (first_word_start = 5.5s)
↑ UtteranceEnd fires here, even though speech continues
```

In this scenario, utterance end fires after detecting the 2-second gap (between when the last word ended at 3.4s and when new speech began at 5.5s), but the speaker was actually continuing their thought. For voice agents that need to wait for truly complete utterances, client-side implementation with additional logic may be more appropriate.

### When to Use Server-Side vs Client-Side Implementation

**Use Deepgram's utterance end when:**
- You need simple, reliable gap detection after finalized words
- You want to minimize client-side processing complexity  
- You're building transcription or note-taking applications

**Consider client-side implementation when:**
- You need to detect gaps within final results for faster response times
- You're building voice agents that require precise utterance boundary detection
- You want to add additional logic (e.g., analyzing speech patterns, semantic completeness)
- You need to customize gap detection behavior beyond what the server provides

**Configuration Requirements:**

| Parameter | Value |
|-----------|-------|
| Minimum | 1,000 ms (default) |
| Maximum | 5,000 ms |
| Step size | Any integer value within range |

<Info>
  **Note for Self-Hosted and Deepgram Dedicated Users:** If your endpoint has a modified step size configuration, the minimum value becomes that step size instead of 1,000 ms. For example:
  - Step size configured for 0.2 (200 ms) → minimum `utterance_end_ms` value is 200
  - Step size configured for 1.5 (1500 ms) → minimum `utterance_end_ms` value is 1500
  
  To learn more about [Deepgram Dedicated](https://deepgram.com/dedicated) or Self-Hosted offerings, reach out to your Deepgram account representative or [contact our sales team](https://deepgram.com/contact-us). For technical details on configuring custom endpoints, see our [Custom Endpoints documentation](https://developers.deepgram.com/reference/custom-endpoints).
</Info>

UtteranceEnd relies on Deepgram's `interim_results` feature and Deepgram's Interim Results are typically sent every second, so using a value of less 1000ms for `utterance_end_ms` will not offer you any benefits.

<Info>
  When using `utterance_end_ms`, setting `interim_results=true` is also required.
</Info>

<CodeGroup>
  ```python Python

  # see https://github.com/deepgram/deepgram-python-sdk/blob/main/examples/streaming/async_microphone/main.py
  # for complete example code

     # Create websocket connection with the required options
     with deepgram.listen.v1.connect(
         model="nova-3",
         language="en-US",
         # Apply smart formatting to the output
         smart_format=True,
         # Raw audio format details
         encoding="linear16",
         channels=1,
         sample_rate=16000,
         # To get UtteranceEnd, the following must be set:
         interim_results=True,
         utterance_end_ms="1000",
         vad_events=True,
         # Time in milliseconds of silence to wait for before finalizing speech
         endpointing=300
     ) as connection:
  ```
</CodeGroup>

## Results

The UtteranceEnd JSON message will look similar to this:

<CodeGroup>
  ```json JSON
  {
    "channel": [
      0,
      1
    ],
    "last_word_end": 2.395,
    "type": "UtteranceEnd"
  }
  ```
</CodeGroup>

* The `type` field is always `UtteranceEnd` for this event.
* The `channel` field is interpreted as `[A,B]`, where `A` is the channel index, and `B` is the total number of channels. The above example is channel 0 of single-channel audio.
* The `last_word_end` field is the time at which end of speech was detected.

If you compare this to the Results response below, you will see that the `last_word_end` from the UtteranceEnd response matches the data in the `alternatives[0].words[1].end` field of the Results response. This is due to the gap identified after the final word.

In addition, you can see `is_final=true`, which is sent because of the `interim_results` feature.

<CodeGroup>
  ```json JSON
  {
    "channel": {
      "alternatives": [
        {
          "confidence": 0.77905273,
          "transcript": "Testing. 123.",
          "words": [
            {
              "confidence": 0.69189453,
              "end": 1.57,
              "punctuated_word": "Testing.",
              "start": 1.07,
              "word": "testing"
            },
            {
              "confidence": 0.77905273,
              "end": 2.395,
              "punctuated_word": "123.",
              "start": 1.895,
              "word": "123"
            }
          ]
        }
      ]
    },
    "channel_index": [
      0,
      1
    ],
    "duration": 1.65,
    "is_final": true,
    "metadata": {
     ...
    "type": "Results"
  }
  ```
</CodeGroup>

***
---
title: Endpointing
subtitle: Endpointing returns transcripts when pauses in speech are detected.
slug: docs/endpointing
---


`endpointing` *string*.

<div class="flex flex-row gap-2">
  <span class="dg-badge unavailable strike-through"><span><Icon icon="file" /> Pre-recorded</span></span>
   <span class="dg-badge"><span><Icon icon="waveform-lines" /> Streaming:Nova</span></span> <span class="dg-badge pink"><span><Icon icon="language" /> All available languages</span></span>
 
</div>

Deepgram’s Endpointing feature can be used for speech detection by monitoring incoming streaming audio and relies on a Voice Activity Detector (VAD), which monitors the incoming audio and triggers when a sufficiently long pause is detected.

Endpointing helps to detects sufficiently long pauses that are likely to represent an endpoint in speech. When an endpoint is detected the model assumes that no additional data will improve it's prediction of the endpoint.

The transcript results are then finalized for the process time range and the JSON response is returned with a `speech_final` parameter set to `true`.

You can customize the length of time used to detect whether a speaker has finished speaking by setting the `endpointing` parameter to an integer value.

<Info>
  Endpointing can be used with Deepgram's [Interim Results](/docs/interim-results/) feature. To compare and contrast these features, and to explore best practices for using them together, see [Using Endpointing and Interim Results with Live Streaming Audio](/docs/understand-endpointing-interim-results/).
</Info>

## Enable Feature

Endpointing is enabled by default and set to 10 milliseconds. and will return transcripts after detecting 10 milliseconds of silence.

The period of silence required for endpointing may also be configured. When you call Deepgram’s API, add an `endpointing` parameter set to an integer by setting endpointing to an integer representing a millisecond value:

`endpointing=500`

This will wait until 500 milliseconds of silence has passed to finalize and return transcripts.

Endpointing may be disabled by setting `endpointing=false`. If endpointing is disabled, transcriptions will be returned at a cadence determined by Deepgram's chunking algorithms.

<CodeGroup>
  ```python Python

  # For help migrating to the new Python SDK, check out our migration guide:
  # https://github.com/deepgram/deepgram-python-sdk/blob/main/docs/Migrating-v3-to-v5.md

     with client.listen.v1.connect(
              model="nova-3",
              language="en-US",
              # Apply smart formatting to the output
              smart_format=True,
              # Raw audio format details
              encoding="linear16",
              channels=1,
              sample_rate=16000,
              # To get UtteranceEnd, the following must be set:
              interim_results=True,
              utterance_end_ms="1000",
              vad_events=True,
              # Time in milliseconds of silence to wait for before finalizing speech
              endpointing=300
     ) as connection:
  ```
</CodeGroup>

## Results

When enabled, the transcript for each received streaming response shows a key called `speech_final`.

<CodeGroup>
  ```json JSON
  {
    "channel_index":[
      0,
      1
    ],
    "duration":1.039875,
    "start":0.0,
    "is_final":false,
    "speech_final":true,
    "channel":{
      "alternatives":[
        {
          "transcript":"another big",
          "confidence":0.9600255,
          "words":[
            {
              "word":"another",
              "start":0.2971154,
              "end":0.7971154,
              "confidence":0.9588303
            },
            {
              "word":"big",
              "start":0.85173076,
              "end":1.039875,
              "confidence":0.9600255
            }
          ]
        }
      ]
    }
  }
  ...
  ```
</CodeGroup>

***
---
title: Interim Results
subtitle: Interim Results provides preliminary results for streaming audio.
slug: docs/interim-results
---


`interim_results` *boolean*. Default: `false`

<div class="flex flex-row gap-2">
  <span class="dg-badge unavailable strike-through"><span><Icon icon="file" /> Pre-recorded</span></span>
   <span class="dg-badge"><span><Icon icon="waveform-lines" /> Streaming:Nova</span></span> <span class="dg-badge pink"><span><Icon icon="language" /> All available languages</span></span>
  
</div>

Deepgram’s Interim Results monitors streaming audio and provides interim transcripts, which are preliminary results provided during the real-time streaming process which can help with speech detection.

Deepgram will identify a point at which its transcript has reached maximum accuracy and send a definitive, or final, transcript of all audio up to that point. It will then continue to process audio.

When working with real-time streaming audio, streams flow from your capture source (for example, microphone, browser, or telephony system) to Deepgram's servers in irregular pieces. In some cases the collected audio can end abruptly—perhaps even mid-word—which means that Deepgram’s predictions, particularly for words near the tip of the audio stream, are more likely to be wrong.

When Interim Results is enabled Deepgram guesses about the words being spoken and sends these guesses to you as interim transcripts. As more audio enters the server, Deepgram corrects and improves the transcriptions, increasing its accuracy, until it reaches the end of the stream, at which point it sends one last, cumulative transcript.

<Info>
  Interim Results can be used with Deepgram's [Endpointing](/docs/endpointing/) feature. To compare and contrast these features, and to explore best practices for using them together, see [Using Endpointing and Interim Results with Live Streaming Audio](/docs/understand-endpointing-interim-results).
</Info>

## Enable Feature

To enable Interim Results, when you call Deepgram’s API, add an `interim_results` parameter set to `true` in the query string:

`interim_results=true`

<CodeGroup>
  ```python Python

  # see https://github.com/deepgram/deepgram-python-sdk/blob/main/examples/streaming/async_microphone/main.py
  # for complete example code

     # Create websocket connection with interim results enabled
     with deepgram.listen.v1.connect(
         model="nova-3",
         language="en-US",
         # Apply smart formatting to the output
         smart_format=True,
         # Raw audio format details
         encoding="linear16",
         channels=1,
         sample_rate=16000,
         # To get interim results, the following must be set:
         interim_results=True,
         utterance_end_ms="1000",
         vad_events=True,
         # Time in milliseconds of silence to wait for before finalizing speech
         endpointing=300
     ) as connection:
  ```
</CodeGroup>

## Analyze Interim Transcripts

Let’s look at some interim transcripts and analyze their content.

Our first interim result has the following content:

<CodeGroup>
  ```json JSON
  {
    "channel_index": [
      0,
      1
    ],
    "duration": 1.039875,
    "start": 0,
    "is_final": false,
    "channel": {
      "alternatives": [
        {
          "transcript": "another big",
          "confidence": 0.9600255,
          "words": [
            {
              "word": "another",
              "start": 0.2971154,
              "end": 0.7971154,
              "confidence": 0.9588303
            },
            {
              "word": "big",
              "start": 0.85173076,
              "end": 1.039875,
              "confidence": 0.9600255
            }
          ]
        }
      ]
    }
  }
  ```
</CodeGroup>

In this response, we see that:

* `start` (the number of seconds into the audio stream) is `0.0`, indicating that this is the very beginning of the real-time stream.
* `start` + `duration` (the entire length of this response) is `1.039875` seconds, and the word "big" ends at `1.039875` seconds (which matches the `duration` value), indicating that the stream cuts off the word.
* `confidence` for the word "big" is approximately 96%, indicating that even though the word is cut off, Deepgram is still pretty certain that its prediction is correct.
* `is_final` is `false`, indicating that Deepgram will continue waiting to see if more data will improve its predictions.

The next interim response has the following content:

<CodeGroup>
  ```json JSON
  {
    "channel_index": [
      0,
      1
    ],
    "duration": 2.039875,
    "start": 0,
    "is_final": false,
    "channel": {
      "alternatives": [
        {
          "transcript": "another big problem",
          "confidence": 0.9939844,
          "words": [
            {
              "word": "another",
              "start": 0.29852942,
              "end": 0.7985294,
              "confidence": 0.9939844
            },
            {
              "word": "big",
              "start": 0.8557843,
              "end": 1.3557843,
              "confidence": 0.98220366
            },
            {
              "word": "problem",
              "start": 1.5722549,
              "end": 2.039875,
              "confidence": 0.9953441
            }
          ]
        }
      ]
    }
  }
  ```
</CodeGroup>

In this response, we see that:

* `start` (the number of seconds into the audio stream) is 0, indicating that this is the very beginning of the real-time stream.
* `start` + `duration` (the entire length of this response) is `2.039875` seconds, and the word "problem" ends at `2.039875` seconds (which matches the `duration` value), indicating that the stream cuts off the word.
* `confidence` for the word "big" has improved to almost 98%.
* the `end` timestamp for "big" now indicates that the word has not been cut off.
* `confidence` for the word "problem" is almost 100%, so can likely be trusted.
* `is_final` is `false`, indicating that Deepgram will continue waiting to see if more data will improve its predictions.

<Info>
  For a more detailed example of using Interim results refer to [Using Interim Results Tips & Tricks](/docs/using-interim-results).
</Info>

***
