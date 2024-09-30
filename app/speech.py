import os
import azure.cognitiveservices.speech as speechsdk
import requests

def transcribe_audio(file_path):
    """
    Transcribe audio using Azure OpenAI Whisper model.
    """
    endpoint = os.getenv('AZURE_WHISPER_ENDPOINT')
    deployment_id = os.getenv('AZURE_WHISPER_DEPLOYMENT_ID')
    api_key = os.getenv('AZURE_WHISPER_API_KEY')

    print(f"Endpoint: {endpoint}")
    print(f"Deployment ID: {deployment_id}")
    print(f"API Key: {api_key}")

    url = f"{endpoint}/openai/deployments/{deployment_id}/audio/transcriptions?api-version=2024-06-01"
    print(f"Transcription URL: {url}")  # 添加调试信息
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'multipart/form-data'
    }
    files = {
        'file': ('audio.wav', open(file_path, 'rb'), 'audio/wav'),
        'model': (None, 'whisper-1')
    }

    response = requests.post(url, headers=headers, files=files)
    print(f"Response status code: {response.status_code}")
    print(f"Response text: {response.text}")
    try:
        response_data = response.json()
        return response_data.get('text', 'Transcription failed')
    except requests.exceptions.JSONDecodeError:
        print("Error decoding JSON response")
        return 'Transcription failed'

def text_to_speech(text, output_file):
    """
    Convert text to speech using Azure Cognitive Services.
    """
    speech_key = os.getenv('AZURE_SPEECH_KEY')
    service_region = os.getenv('AZURE_SERVICE_REGION')

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
