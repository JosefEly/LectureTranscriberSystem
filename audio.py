import re
from mlx_audio.stt import load
import datetime
import shutil
import os
from ollama import chat
import assemblyai as aai
import librosa
import mlx.core as mx


aai.settings.api_key = os.environ["ASSEMBLYAI_API_KEY"]


#This function sends the audio file at an input path to AssemblyAI for transcription, as opposed to using a slower but more private local model

def assembly_transcribe(filepath, prompt=None):
	config = aai.TranscriptionConfig(
	language_detection=True,
	prompt=prompt,)

	transcript = aai.Transcriber().transcribe(filepath, config)
	fulltext = (transcript.text)
	sentences = re.split(r'(?<=[\.?!] )', fulltext)
	fulltext = ""
	count = 0
	for item in sentences:
		fulltext += item
		fulltext += "\n"
		fulltext += "\n"
	return(fulltext)


def list_audio():
	file_list = os.listdir(os.getcwd())
	file_audio = []
	for item in file_list:
		if ".m4a" in item and item not in file_audio:
			file_audio.append(item)
	return (file_audio)

# Lists the files in the current directory using os.getcwd()
# Adds each unique file ending in .m4a to a list and returns it

def ollama_chat(input):
	response = chat(
        model='qwen3.5:9b',

        messages=[{'role': 'user', 'content': input}],
	
	options={
        'num_ctx': 8192,      # Increase context window to 8k tokens
        'num_predict': -1,     # Allow unlimited generation until it finishes
    	"think": False
	},
	
	keep_alive=0
	)
	return response.message.content
# This function takes in an input string and passes it through qwen3.5 9b, with the context set high, and the model set to expunge itself from memory after use


def qwen_transcribe(filepath, prompt=None):
	filepath = "./" + filepath
	model = load("mlx-community/Qwen3-ASR-1.7B-8bit", system_prompt=prompt, )
	result = model.generate(filepath, language="English", chunk_duration=300.0, overlap_duration = 15.0)
	fulltext = result.text

	import gc
	del model
	gc.collect()
	mx.clear_cache()	

	sentences = re.split(r'(?<=[\.?!] )', fulltext)
	fulltext = ""
	count = 0
	for item in sentences:
		fulltext += item
		fulltext += "\n"
		fulltext += "\n"	
	return(fulltext)

# Qwen_transcribe loads the Qwen ASR model into memory, with a system prompt as input. It then has the model generate response text, splits the output text around punctuation, adds two newlines between each sentence, and returns the altered text
		

def chunk_text(text):
	if len(text) < 5500:
		return text
	else:
		return(text[:2499] + "\n" + "-chunk separator-" + "\n"+  text[-2500:])

# The point of this is to give the model's 5000 characters more sections of conversation covered
def sort_transcript(text):
	text = chunk_text(text)
	directory_list = os.listdir(os.getcwd())	
	transcript_dirs = [item for item in directory_list if "_transcripts" in item and ".txt" not in item]
	dirs_descriptions = {}
	for item in transcript_dirs:
		file = open(f"{item}/folder_description.txt")
		contents = file.read()
		dirs_descriptions[item] = contents

# The function lists the files inside the current directory, and records the subset of them that end with "_transcripts" and are not text files. It then opens the folder description file inside each of them and adds it to a dictonary of folders with descriptions
	sorting_prompt = """

You are taking in two fragment of a conversation transcript (up to 5,000 characters, cut off if more) and a set of directory descriptions. Your goal is to sort the transcript into the correct directory among the listed directories, by picking the directory whose description is the strongest match for the content of the transcript. You will also provide a confidence score for your decision, which should be an integer between 1 and 10, where 1 is minimal confidence and 10 is maximal confidence. After you have determined the target directory, provide a short summary of the transcript domain and topic. This should be ten words or less. Do this based on your transcript fragment, and your knowlege of what folder it goes in and the subjects it covers. This is intended for use by a speech-recognition model that accepts a system prompt. It should be less than 150 words. You should list your response to these criteria in a Python dictonary format.

The dictonary should be structured as followed:
If the most likely directory is foo, and you have confidence 8, and you have generated a summary and term guide 'EXAMPLE SUMMARY TEXT', you should output:
{"directory_name": "foo", "confidence_score": 8, "summary": "EXAMPLE SUMMARY TEXT"}
Below is the list of possible directories and their descriptions, followed by the transcript to categorize.
"""
	for item in dirs_descriptions.keys():
		sorting_prompt += "\nDirectory Name: \n"
		sorting_prompt += item
		sorting_prompt += "\nDirectiory Description\n"
		sorting_prompt += dirs_descriptions[item]
		sorting_prompt += "\n"
	sorting_prompt += "Transcript\n"
	sorting_prompt += text[:5000]
	sorting_prompt += "\n\nEND OF TRANSCRIPT. Output the directory this transcript belongs in using the dictonary format I designated earlier."
	response_text = None
# This function then creates a system prompt for the LLM that contains all the folder names, the transcript, and how to classify the transcript.

	import ast
	count = 0
	while response_text == None and count < 5:
		try:	
			print(count)
			response_text = (ollama_chat(sorting_prompt))
			print(response_text)
			response_text = re.search("{[^}]+}", response_text).group()
			response_text = ast.literal_eval(response_text)
		
			if (response_text["directory_name"]) not in transcript_dirs:
				response_text = None
				count += 1
				continue
			if "summary" not in response_text:
				response_text = None
				count  += 1
				continue
		except Exception:
			print(Exception)
			response_text = None
			count += 1
			continue
	return(response_text)

# This function then returns the response_text object from ollama containing the target directory, transcript overview, and confidence score.
def write_transcript(filename):

	from mlx_audio.stt import load
	model = load("mlx-community/parakeet-tdt-0.6b-v2")
	y, sr = librosa.load(path=filename, offset=0.0, duration=600.0, sr=model.preprocessor_config.sample_rate)
	# This returns a numpy array
	y = mx.array(y)
	# It is then converted into a MLX array and fed to the STT model
	result =  model.generate(y, chunk_duration=300.0, overlap_duration = 15.0)
	fulltext = ""
	for sentence in result.sentences:
		fulltext += (sentence.text)
		fulltext += ("\n")
	filestat = os.stat(filename)
	import gc
	del model
	gc.collect()
	mx.clear_cache()

	response_text = sort_transcript(fulltext)
	# At this point, the function prints the directory the transcript has been sorted into based on an analysis of the first 600 seconds of the audio file.
	print(response_text)
	if response_text == None:
		print("Ollama Error")
		return None
	if "PUBLIC" in response_text["directory_name"]:
		qwen_text = assembly_transcribe(filename, response_text["summary"])
	else:
		qwen_text = qwen_transcribe(filename, response_text["summary"])
	#If the output folder is marked as public (containing non-sensitive data, like classes), it will be sent to an external service, which is more accurate, for transcription
	#Otherwise it is transcribed locally.	
	folderroot = re.sub(r"_.+","", response_text["directory_name"])
	filewrite = folderroot + "_" + datetime.datetime.fromtimestamp(filestat.st_birthtime).strftime("%m-%d-%Y-%H-%M") + ".txt"
	#This software writes the transcript to a text file in the following format: folder root name_(date of classification)(month-day-year-hour-minute).txt
	transcripts = folderroot + "_transcripts"
	audio = folderroot + "_audio"
	# This program works by appending preprogrammed suffixes (audio or transcripts) to the directory root name, and moving the audio and transcripts to the folder with the appropriate suffixes
	with open(f"{transcripts}/{filewrite}", "w") as text:
		text.write(qwen_text)
	shutil.move(filename, f"{audio}/{filename}")
	print(filewrite)


	
for item in list_audio():
	write_transcript(item)

# The program currently runs one pass over all the audio files inside the directory when run, which you can do after class.
