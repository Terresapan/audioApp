---
title: Close Stream
subtitle: Send a CloseStream message to close the WebSocket stream.
slug: docs/close-stream
---

<div class="flex flex-row gap-2">
  <span class="dg-badge"><span><Icon icon="waveform-lines" /> Streaming:Nova</span></span>
</div>

Use the `CloseStream` message to close the WebSocket stream. This forces the server to immediately process any unprocessed audio data and return the final transcription results.

## Purpose

In real-time audio processing, there are scenarios where you may need to force the server to close. Deepgram supports a `CloseStream` message to handle such situations. This message will send a shutdown command to the server instructing it to finish processing any cached data, send the response to the client, send a summary metadata object, and then terminate the WebSocket connection.

## Example Payloads

To send the `CloseStream` message, you need to send the following JSON message to the server:

<CodeGroup>
  ```json JSON
  {
    "type": "CloseStream"
  }
  ```
</CodeGroup>

Upon receiving the `CloseStream` message, the server will process all remaining audio data and return the following:

<CodeGroup>
  ```json JSON
  {
      "type": "Metadata",
      "transaction_key": "deprecated",
      "request_id": "8c8ebea9-dbec-45fa-a035-e4632cb05b5f",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "created": "2024-08-29T22:37:55.202Z",
      "duration": 0.0,
      "channels": 0
  }
  ```
</CodeGroup>

## Language-Specific Implementations

Below are code examples to help you get started using `CloseStream`.

<CodeGroup>
  ```javascript JavaScript
  const WebSocket = require("ws");

  // Assuming 'headers' is already defined for authorization
  const ws = new WebSocket("wss://api.deepgram.com/v1/listen", { headers });

  ws.on('open', function open() {
    // Construct CloseStream message
    const closeStreamMsg = JSON.stringify({ type: "CloseStream" });

    // Send CloseStream message
    ws.send(closeStreamMsg);
  });
  ```

  ```python Python
  import json
  import websocket

  # Assuming 'headers' is already defined for authorization
  ws = websocket.create_connection("wss://api.deepgram.com/v1/listen", header=headers)

  # Construct CloseStream message
  closestream_msg = json.dumps({"type": "CloseStream"})

  # Send CloseStream message
  ws.send(closestream_msg)
  ```

  ```go Go
  package main

  import (
      "encoding/json"
      "log"
      "net/http"
      "github.com/gorilla/websocket"
  )

  func main() {
      // Define headers for authorization
      headers := http.Header{}
      headers.Add("Authorization", "Bearer YOUR_API_KEY") // Replace with your actual API key

      // Connect to the WebSocket server
      conn, _, err := websocket.DefaultDialer.Dial("wss://api.deepgram.com/v1/listen", headers)
      if err != nil {
          log.Fatal("Error connecting to WebSocket:", err)
      }
      defer conn.Close()

      // Construct CloseStream message
      closeStreamMsg := map[string]string{"type": "CloseStream"}
      jsonMsg, err := json.Marshal(closeStreamMsg)
      if err != nil {
          log.Fatal("Error encoding JSON:", err)
      }

      // Send CloseStream message
      err = conn.WriteMessage(websocket.TextMessage, jsonMsg)
      if err != nil {
          log.Fatal("Error sending CloseStream message:", err)
      }
  }
  ```

  ```csharp C#
  using System;
  using System.Net.WebSockets;
  using System.Text;
  using System.Threading;
  using System.Threading.Tasks;

  class Program
  {
      static async Task Main(string[] args)
      {
          // Set up the WebSocket URL and headers
          Uri uri = new Uri("wss://api.deepgram.com/v1/listen");
          string apiKey = "YOUR_API_KEY"; // Replace with your actual API key

          // Create a new client WebSocket instance
          using (ClientWebSocket ws = new ClientWebSocket())
          {
              // Set the authorization header
              ws.Options.SetRequestHeader("Authorization", "Token " + apiKey);

              try
              {
                  // Connect to the WebSocket server
                  await ws.ConnectAsync(uri, CancellationToken.None);

                  // Construct the CloseStream message
                  string closeStreamMsg = "{\"type\": \"CloseStream\"}";

                  // Convert the CloseStream message to a byte array
                  byte[] finalizeBytes = Encoding.UTF8.GetBytes(closeStreamMsg);

                  // Send the CloseStream message asynchronously
                  await ws.SendAsync(new ArraySegment<byte>(finalizeBytes), WebSocketMessageType.Text, true, CancellationToken.None);
              }
              catch (WebSocketException ex)
              {
                  Console.WriteLine("WebSocket error: " + ex.Message);
              }
              catch (Exception ex)
              {
                  Console.WriteLine("General error: " + ex.Message);
              }
          }
      }
  }
  ```
</CodeGroup>

***

---
title: Finalize
subtitle: Send a Finalize message to flush the WebSocket stream.
slug: docs/finalize
---

<div class="flex flex-row gap-2">
  <span class="dg-badge"><span><Icon icon="waveform-lines" /> Streaming:Nova</span></span>
</div>

Use the `Finalize` message to flush the WebSocket stream. This forces the server to immediately process any unprocessed audio data and return the final transcription results.

## Purpose

In real-time audio processing, there are scenarios where you may need to force the server to process (*or flush*) all unprocessed audio data immediately. Deepgram supports a `Finalize` message to handle such situations, ensuring that interim results are treated as final.

## Example Payloads

To send the `Finalize` message, you need to send the following JSON message to the server:

<CodeGroup>
  ```json JSON
  {
    "type": "Finalize"
  }
  ```
</CodeGroup>

You can optionally specify a `channel` field to finalize a specific channel. If the `channel` field is omitted, all channels in the audio will be finalized. Note that channel indexing starts at 0, so to finalize only the *first* channel you need to send:

<CodeGroup>
  ```json JSON
  {
    "type": "Finalize",
     "channel": 0
  }
  ```
</CodeGroup>

Upon receiving the Finalize message, the server will process all remaining audio data and return the final results. You may receive a response with the `from_finalize` attribute set to `true`, indicating that the finalization process is complete. This response typically occurs when there is a noticeable amount of audio buffered in the server.

If you specified a `channel` to be finalized, use the response's `channel_index` field to check which channel was finalized.

<CodeGroup>
  ```json JSON
  {
    "from_finalize": true
  }
  ```
</CodeGroup>

<Info>
  In most cases, you will receive this response, but it is not guaranteed if there is no significant amount of audio data to process.
</Info>

## Language-Specific Implementations

Below are code examples to help you get started using `Finalize`.

### Sending a `Finalize` message in JSON Format

These snippets demonstrate how to construct a JSON message containing the "Finalize" type and send it over the WebSocket connection in each respective language.

<CodeGroup>
  ```javascript JavaScript
  const WebSocket = require("ws");

  // Assuming 'headers' is already defined for authorization
  const ws = new WebSocket("wss://api.deepgram.com/v1/listen", { headers });

  ws.on('open', function open() {
    // Construct Finalize message
    const finalizeMsg = JSON.stringify({ type: "Finalize" });

    // Send Finalize message
    ws.send(finalizeMsg);
  });
  ```

  ```python Python
  import json
  import websocket

  # Assuming 'headers' is already defined for authorization
  ws = websocket.create_connection("wss://api.deepgram.com/v1/listen", header=headers)

  # Construct Finalize message
  finalize_msg = json.dumps({"type": "Finalize"})

  # Send Finalize message
  ws.send(finalize_msg)
  ```

  ```go Go
  package main

  import (
      "encoding/json"
      "log"
      "net/http"
      "github.com/gorilla/websocket"
  )

  func main() {
      // Define headers for authorization
      headers := http.Header{}

      // Assuming headers are set here for authorization
      conn, _, err := websocket.DefaultDialer.Dial("wss://api.deepgram.com/v1/listen", headers)
      if err != nil {
          log.Fatal("Error connecting to WebSocket:", err)
      }
      defer conn.Close()

      // Construct Finalize message
      finalizeMsg := map[string]string{"type": "Finalize"}
      jsonMsg, err := json.Marshal(finalizeMsg)
      if err != nil {
          log.Fatal("Error encoding JSON:", err)
      }

      // Send Finalize message
      err = conn.WriteMessage(websocket.TextMessage, jsonMsg)
      if err != nil {
          log.Fatal("Error sending Finalize message:", err)
      }
  }
  ```

  ```csharp C#
  using System;
  using System.Net.WebSockets;
  using System.Text;
  using System.Threading;
  using System.Threading.Tasks;

  class Program
  {
      static async Task Main(string[] args)
      {
          // Set up the WebSocket URL and headers
          Uri uri = new Uri("wss://api.deepgram.com/v1/listen");

          string apiKey = "DEEPGRAM_API_KEY";

          // Create a new client WebSocket instance
          using (ClientWebSocket ws = new ClientWebSocket())
          {
              // Set the authorization header
              ws.Options.SetRequestHeader("Authorization", "Token " + apiKey);

              // Connect to the WebSocket server
              await ws.ConnectAsync(uri, CancellationToken.None);

              // Construct the Finalize message
              string finalizeMsg = "{\"type\": \"Finalize\"}";

              // Convert the Finalize message to a byte array
              byte[] finalizeBytes = Encoding.UTF8.GetBytes(finalizeMsg);

              // Send the Finalize message asynchronously
              await ws.SendAsync(new ArraySegment<byte>(finalizeBytes), WebSocketMessageType.Text, true, CancellationToken.None);
          }
      }
  }
  ```
</CodeGroup>

### Streaming Examples

Here are more complete examples that make a streaming request and use Finalize. Try running these examples to see how Finalize can be sent to Deepgram, forcing the API to process all unprocessed audio data and immediately return the results.

<CodeGroup>
  ```javascript JavaScript
  const WebSocket = require("ws");
  const axios = require("axios");
  const { PassThrough } = require("stream");

  const apiKey = "YOUR_DEEPGRAM_API_KEY";
  const headers = {
    Authorization: `Token ${apiKey}`,
  };

  // Initialize WebSocket connection
  const ws = new WebSocket("wss://api.deepgram.com/v1/listen", { headers });

  ws.on("open", async function open() {
    console.log("WebSocket connection established.");

    try {
      // Fetch the audio stream from the remote URL
      const response = await axios({
        method: "get",
        url: "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
        responseType: "stream",
      });

      const passThrough = new PassThrough();
      response.data.pipe(passThrough);

      passThrough.on("data", (chunk) => {
        ws.send(chunk);
      });

      passThrough.on("end", () => {
        console.log("Audio stream ended.");
        finalizeWebSocket();
      });

      passThrough.on("error", (err) => {
        console.error("Stream error:", err.message);
      });

      // Send Finalize message after 10 seconds
      setTimeout(() => {
        finalizeWebSocket();
      }, 10000);
    } catch (error) {
      console.error("Error fetching audio stream:", error.message);
    }
  });

  // Handle WebSocket message event
  ws.on("message", function incoming(data) {
    let response = JSON.parse(data);
    if (response.type === "Results") {
      console.log("Transcript: ", response.channel.alternatives[0].transcript);
    }
  });

  // Handle WebSocket close event
  ws.on("close", function close() {
    console.log("WebSocket connection closed.");
  });

  // Handle WebSocket error event
  ws.on("error", function error(err) {
    console.error("WebSocket error:", err.message);
  });

  // Send Finalize message to WebSocket
  function finalizeWebSocket() {
    const finalizeMsg = JSON.stringify({ type: "Finalize" });
    ws.send(finalizeMsg);
    console.log("Finalize message sent.");
  }

  // Gracefully close the WebSocket connection when done
  function closeWebSocket() {
    const closeMsg = JSON.stringify({ type: "CloseStream" });
    ws.send(closeMsg);
    ws.close();
  }

  // Close WebSocket when process is terminated
  process.on("SIGINT", () => {
    closeWebSocket();
    process.exit();
  });
  ```

  ```python Python
  from websocket import WebSocketApp
  import websocket
  import json
  import threading
  import requests
  import time

  auth_token = "YOUR_DEEPGRAM_API_KEY"  # Replace with your actual authorization token

  headers = {
      "Authorization": f"Token {auth_token}"
  }

  # WebSocket URL
  ws_url = "wss://api.deepgram.com/v1/listen"

  # Audio stream URL
  audio_url = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"

  # Define the WebSocket functions on_open, on_message, on_close, and on_error

  def on_open(ws):
      print("WebSocket connection established.")

      # Start audio streaming thread
      audio_thread = threading.Thread(target=stream_audio, args=(ws,))
      audio_thread.daemon = True
      audio_thread.start()

      # Finalize test thread
      finalize_thread = threading.Thread(target=finalize_test, args=(ws,))
      finalize_thread.daemon = True
      finalize_thread.start()

  def on_message(ws, message):
      try:
          response = json.loads(message)
          if response.get("type") == "Results":
              transcript = response["channel"]["alternatives"][0].get("transcript", "")
              if transcript:
                  print("Transcript:", transcript)

              # Check if this is the final result from finalize
              # Note: in most cases, you will receive this response, but it is not guaranteed if there is no significant amount of audio data left to process.
              if response.get("from_finalize", False):
                  print("Finalization complete.")
      except json.JSONDecodeError as e:
          print(f"Error decoding JSON message: {e}")
      except KeyError as e:
          print(f"Key error: {e}")

  def on_close(ws, close_status_code, close_msg):
      print(f"WebSocket connection closed with code: {close_status_code}, message: {close_msg}")

  def on_error(ws, error):
      print("WebSocket error:", error)

  # Define the function to stream audio to the WebSocket

  def stream_audio(ws):
      response = requests.get(audio_url, stream=True)
      if response.status_code == 200:
          print("Audio stream opened.")
          for chunk in response.iter_content(chunk_size=4096):
              ws.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)
      else:
          print("Failed to open audio stream:", response.status_code)

  # Define the function to send the Finalize message

  def finalize_test(ws):
      # Wait for 10 seconds before sending the Finalize message to simulate the end of audio streaming
      time.sleep(10)
      finalize_message = json.dumps({"type": "Finalize"})
      ws.send(finalize_message)
      print("Finalize message sent.")

  # Create WebSocket connection

  ws = WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_close=on_close, on_error=on_error, header=headers)

  # Run the WebSocket

  ws.run_forever()
  ```
</CodeGroup>

***

---
title: Audio Keep Alive
subtitle: Send keep alive messages while streaming audio to keep the connection open.
slug: docs/audio-keep-alive
---

<div class="flex flex-row gap-2">
  <span class="dg-badge"><span><Icon icon="waveform-lines" /> Streaming:Nova</span></span>
</div>

Use the `KeepAlive` message to keep your WebSocket connection open during periods of silence, preventing timeouts and optimizing costs.

## Purpose

 Send a `KeepAlive` message every 3-5 seconds to prevent the 10-second timeout that triggers a `NET-0001` error and closes the connection. Ensure the message is sent as a text WebSocket frame—sending it as binary may result in incorrect handling and potential connection issues.

## Example Payloads

To send the `KeepAlive` message, send the following JSON message to the server:

<CodeGroup>
  ```json JSON
  {
    "type": "KeepAlive"
  }
  ```
</CodeGroup>

The server will not send a response back when you send a `KeepAlive` message. If no audio data or `KeepAlive` messages are sent within a 10-second window, the connection will close with a `NET-0001` error.

## Language Specific Implementations

Below are code examples to help you get started using `KeepAlive`.

### Sending a `KeepAlive` message in JSON Format

Construct a JSON message containing the `KeepAlive` type and send it over the WebSocket connection in each respective language.

<CodeGroup>
  ```javascript JavaScript
  const WebSocket = require("ws");

  // Assuming 'headers' is already defined for authorization
  const ws = new WebSocket("wss://api.deepgram.com/v1/listen", { headers });

  // Assuming 'ws' is the WebSocket connection object
  const keepAliveMsg = JSON.stringify({ type: "KeepAlive" });
  ws.send(keepAliveMsg);
  ```

  ```python Python
  import json
  import websocket

  # Assuming 'headers' is already defined for authorization
  ws = websocket.create_connection("wss://api.deepgram.com/v1/listen", header=headers)

  # Assuming 'ws' is the WebSocket connection object
  keep_alive_msg = json.dumps({"type": "KeepAlive"})
  ws.send(keep_alive_msg)
  ```

  ```go Go
  package main

  import (
      "encoding/json"
      "log"
      "net/http"
      "github.com/gorilla/websocket"
  )

  func main() {
      // Define headers for authorization
      headers := http.Header{}

    	// Assuming headers are set here for authorization
      conn, _, err := websocket.DefaultDialer.Dial("wss://api.deepgram.com/v1/listen", headers)
      if err != nil {
          log.Fatal("Error connecting to WebSocket:", err)
      }
      defer conn.Close()

      // Construct KeepAlive message
      keepAliveMsg := map[string]string{"type": "KeepAlive"}
      jsonMsg, err := json.Marshal(keepAliveMsg)
      if err != nil {
          log.Fatal("Error encoding JSON:", err)
      }

      // Send KeepAlive message
      err = conn.WriteMessage(websocket.TextMessage, jsonMsg)
      if err != nil {
          log.Fatal("Error sending KeepAlive message:", err)
      }
  }
  ```

  ```csharp C#
  using System;
  using System.Net.WebSockets;
  using System.Text;
  using System.Threading;
  using System.Threading.Tasks;

  class Program
  {
      static async Task Main(string[] args)
      {
          // Set up the WebSocket URL and headers
          Uri uri = new Uri("wss://api.deepgram.com/v1/listen");

          string apiKey = "DEEPGRAM_API_KEY";

          // Create a new client WebSocket instance
          using (ClientWebSocket ws = new ClientWebSocket())
          {
              // Set the authorization header
              ws.Options.SetRequestHeader("Authorization", "Token " + apiKey);

              // Connect to the WebSocket server
              await ws.ConnectAsync(uri, CancellationToken.None);

              // Construct the KeepAlive message
              string keepAliveMsg = "{\"type\": \"KeepAlive\"}";

              // Convert the KeepAlive message to a byte array
              byte[] keepAliveBytes = Encoding.UTF8.GetBytes(keepAliveMsg);

              // Send the KeepAlive message asynchronously
              await ws.SendAsync(new ArraySegment<byte>(keepAliveBytes), WebSocketMessageType.Text, true, CancellationToken.None);
          }
      }
  }
  ```
</CodeGroup>

### Streaming Examples

Make a streaming request and use `KeepAlive` to keep the connection open.

<CodeGroup>
  ```javascript JavaScript
  const WebSocket = require("ws");

  const authToken = "DEEPGRAM_API_KEY"; // Replace 'DEEPGRAM_API_KEY' with your actual authorization token
  const headers = {
    Authorization: `Token ${authToken}`,
  };

  // Initialize WebSocket connection
  const ws = new WebSocket("wss://api.deepgram.com/v1/listen", { headers });

  // Handle WebSocket connection open event
  ws.on("open", function open() {
    console.log("WebSocket connection established.");

    // Send audio data (replace this with your audio streaming logic)
    // Example: Read audio from a microphone and send it over the WebSocket
    // For demonstration purposes, we're just sending a KeepAlive message

    setInterval(() => {
      const keepAliveMsg = JSON.stringify({ type: "KeepAlive" });
      ws.send(keepAliveMsg);
      console.log("Sent KeepAlive message");
    }, 3000); // Sending KeepAlive messages every 3 seconds
  });

  // Handle WebSocket message event
  ws.on("message", function incoming(data) {
    console.log("Received:", data);
    // Handle received data (transcription results, errors, etc.)
  });

  // Handle WebSocket close event
  ws.on("close", function close() {
    console.log("WebSocket connection closed.");
  });

  // Handle WebSocket error event
  ws.on("error", function error(err) {
    console.error("WebSocket error:", err.message);
  });

  // Gracefully close the WebSocket connection when done
  function closeWebSocket() {
    const closeMsg = JSON.stringify({ type: "CloseStream" });
    ws.send(closeMsg);
  }

  // Call closeWebSocket function when you're finished streaming audio
  // For example, when user stops recording or when the application exits
  // closeWebSocket();
  ```

  ```python Python
  import websocket
  import json
  import time
  import threading

  auth_token = "DEEPGRAM_API_KEY"  # Replace 'DEEPGRAM_API_KEY' with your actual authorization token
  headers = {
      "Authorization": f"Token {auth_token}"
  }

  # WebSocket URL
  ws_url = "wss://api.deepgram.com/v1/listen"

  # Define the WebSocket on_open function
  def on_open(ws):
      print("WebSocket connection established.")
      # Send KeepAlive messages every 3 seconds
      def keep_alive():
          while True:
              keep_alive_msg = json.dumps({"type": "KeepAlive"})
              ws.send(keep_alive_msg)
              print("Sent KeepAlive message")
              time.sleep(3)
      # Start a thread for sending KeepAlive messages
      keep_alive_thread = threading.Thread(target=keep_alive)
      keep_alive_thread.daemon = True
      keep_alive_thread.start()

  # Define the WebSocket on_message function
  def on_message(ws, message):
      print("Received:", message)
      # Handle received data (transcription results, errors, etc.)

  # Define the WebSocket on_close function
  def on_close(ws):
      print("WebSocket connection closed.")

  # Define the WebSocket on_error function
  def on_error(ws, error):
      print("WebSocket error:", error)

  # Create WebSocket connection
  ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_close=on_close,
                              on_error=on_error,
                              header=headers)

  # Run the WebSocket
  ws.run_forever()
  ```
</CodeGroup>

## Using Deepgram SDKs

Deepgram's SDKs make it easier to build with Deepgram in your preferred language.
For more information on using Deepgram SDKs, refer to the SDKs documentation in the GitHub Repository.

* [JS SDK](https://github.com/deepgram/deepgram-js-sdk)
* [Python SDK](https://github.com/deepgram/deepgram-python-sdk)
* [Go SDK](https://github.com/deepgram/deepgram-go-sdk)
* [.NET SDK](https://github.com/deepgram/deepgram-dotnet-sdk)

<CodeGroup>
  ```javascript JavaScript
  const { createClient, LiveTranscriptionEvents } = require("@deepgram/sdk");

  const live = async () => {
    const deepgram = createClient("DEEPGRAM_API_KEY");
    let connection;
    let keepAlive;

    const setupDeepgram = () => {
      connection = deepgram.listen.live({
        model: "nova-3",
        utterance_end_ms: 1500,
        interim_results: true,
      });

      if (keepAlive) clearInterval(keepAlive);
      keepAlive = setInterval(() => {
        console.log("KeepAlive sent.");
        connection.keepAlive();
      }, 3000); // Sending KeepAlive messages every 3 seconds

      connection.on(LiveTranscriptionEvents.Open, () => {
        console.log("Connection opened.");
      });

      connection.on(LiveTranscriptionEvents.Close, () => {
        console.log("Connection closed.");
        clearInterval(keepAlive);
      });

      connection.on(LiveTranscriptionEvents.Metadata, (data) => {
        console.log(data);
      });

      connection.on(LiveTranscriptionEvents.Transcript, (data) => {
        console.log(data.channel);
      });

      connection.on(LiveTranscriptionEvents.UtteranceEnd, (data) => {
        console.log(data);
      });

      connection.on(LiveTranscriptionEvents.SpeechStarted, (data) => {
        console.log(data);
      });

      connection.on(LiveTranscriptionEvents.Error, (err) => {
        console.error(err);
      });
    };

    setupDeepgram();
  };

  live();
  ```

  ```python Python
  # For help migrating to the new Python SDK, check out our migration guide:
  # https://github.com/deepgram/deepgram-python-sdk/blob/main/docs/Migrating-v3-to-v5.md

  import os
  from deepgram import DeepgramClient
  from deepgram.core.events import EventType

  API_KEY = os.getenv("DEEPGRAM_API_KEY")

  def main():
      try:
          deepgram = DeepgramClient(
              api_key=API_KEY,
              config={"keepalive": "true"} # Comment this out to see the effect of not using keepalive
          )

          with deepgram.listen.websocket.v('1').stream(
              model="nova-3",
              language="en-US",
              smart_format=True,
          ) as dg_connection:

              def on_message(result):
                  if hasattr(result, 'channel') and result.channel.alternatives:
                      sentence = result.channel.alternatives[0].transcript
                      if len(sentence) == 0:
                          return
                      print(f"speaker: {sentence}")

              def on_metadata(result):
                  print(f"\n\n{result}\n\n")

              def on_error(error):
                  print(f"\n\n{error}\n\n")

              dg_connection.on(EventType.MESSAGE, on_message)
              dg_connection.on(EventType.METADATA, on_metadata)
              dg_connection.on(EventType.ERROR, on_error)

              dg_connection.start_listening()

      except Exception as e:
          print(f"Could not open socket: {e}")

  if __name__ == "__main__":
      main()
  ```

  ```go Go
  package main

  import (
  	"bufio"
  	"context"
  	"fmt"
  	"os"

  	interfaces "github.com/deepgram/deepgram-go-sdk/pkg/client/interfaces"
  	client "github.com/deepgram/deepgram-go-sdk/pkg/client/live"
  )

  func main() {
  	// init library
  	client.InitWithDefault()

  	// Go context
  	ctx := context.Background()

  	// set the Transcription options
  	tOptions := interfaces.LiveTranscriptionOptions{
  		Model="nova-3",
      Language:  "en-US",
  		Punctuate: true,
  	}

  	// create a Deepgram client
  	cOptions := interfaces.ClientOptions{
  		EnableKeepAlive: true, // Comment this out to see the effect of not using keepalive
  	}

  	// use the default callback handler which just dumps all messages to the screen
  	dgClient, err := client.New(ctx, "", cOptions, tOptions, nil)
  	if err != nil {
  		fmt.Println("ERROR creating LiveClient connection:", err)
  		return
  	}

  	// connect the websocket to Deepgram
  	wsconn := dgClient.Connect()
  	if wsconn == nil {
  		fmt.Println("Client.Connect failed")
  		os.Exit(1)
  	}

  	// wait for user input to exit
  	fmt.Printf("This demonstrates using KeepAlives. Press ENTER to exit...\n")
  	input := bufio.NewScanner(os.Stdin)
  	input.Scan()

  	// close client
  	dgClient.Stop()

  	fmt.Printf("Program exiting...\n")
  }
  ```
</CodeGroup>

## Word Timings

Word timings in streaming transcription results are based on the audio stream itself, not the lifetime of the WebSocket connection. If you send KeepAlive messages without any audio payloads for a period of time, then resume sending audio, the timestamps will continue from where the audio left off—not from when the KeepAlive messages were sent.

Here is an example timeline demonstrating the behavior.

| Event                                                            | Wall Time  | Word Timing Range on Results Response |
| ---------------------------------------------------------------- | ---------- | ------------------------------------- |
| Websocket opened, begin sending audio payloads                   | 0 seconds  | 0 seconds                             |
| Results received                                                 | 5 seconds  | 0-5 seconds                           |
| Results received                                                 | 10 seconds | 5-10 seconds                          |
| Pause sending audio payloads, while sending `KeepAlive` messages | 10 seconds | *n/a*                                 |
| Resume sending audio payloads                                    | 30 seconds | *n/a*                                 |
| Results received                                                 | 35 seconds | 10-15 seconds                         |

***


