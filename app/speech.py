import os
import azure.cognitiveservices.speech as speechsdk
import openai

# Initialize the OpenAI client
openai.api_key = os.getenv('AZURE_OPENAI_API_KEY')

def transcribe_audio(file_path):
    """
    Transcribe audio using Azure OpenAI Whisper model.
    """
    with open(file_path, 'rb') as audio_file:
        response = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file
        )
    return response['text']

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
