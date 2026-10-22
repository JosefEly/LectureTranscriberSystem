import re
from mlx_audio.stt import load
#mlx-community/parakeet-tdt-0.6b-v3
# Load the multilingual v3 model
import datetime
import shutil

# ['.txt', '.DS_Store', 'bin', 'Consulting_audio', 'include', 'Other', 'pyvenv.cfg', '..txt', 'Beverly 7:2:26.m4a', 'lib', 'audio.py', '.git', 'Consulting_transcripts', 'archived', 'Beverly.m4a', 'Allie Penam.m4a', 'share']


import os


from ollama import chat
"""
response = chat(
    model='qwen3.5:9b',
    messages=[{'role': 'user', 'content': 'Hello!'}], keep_alive=0
)
print(response.message.content)
"""



def list_audio():
	file_list = os.listdir(os.getcwd())
	file_audio = []
	for item in file_list:
		if ".m4a" in item and item not in file_audio:
			file_audio.append(item)
	return (file_audio)

def ollama_chat(input):
	response = chat(
        model='qwen3.5:9b',
        messages=[{'role': 'user', 'content': input}],stream=False, options={
        'num_ctx': 8192,      # Increase context window to 8k tokens
        'num_predict': -1,     # Allow unlimited generation until it finishes
    	"think": False
	}, keep_alive=0
	)
	return response.message.content

def qwen_transcribe(filepath, prompt=None):
	model = load("mlx-community/Qwen3-ASR-1.7B-8bit", system_prompt=prompt, )
	result = model.generate(filepath, language="English", chunk_duration=300.0, overlap_duration = 15.0)
	fulltext = result.text
	import gc
	import mlx.core as mx
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
		
def sort_transcript(text):
	directory_list = os.listdir(os.getcwd())	
	transcript_dirs = [item for item in directory_list if "_transcripts" in item and ".txt" not in item]
	dirs_descriptions = {}
	for item in transcript_dirs:
		file = open(f"{item}/folder_description.txt")
		contents = file.read()
		dirs_descriptions[item] = contents
	sorting_prompt = """

You are taking in a conversation transcript (up to 10,000 characters, cut off if more) and a set of directory descriptions. Your goal is to sort the transcript into the correct directory among the listed directories, by picking the directory whose description is the strongest match for the content of the transcript. You will also provide a confidence score for your decision, which should be an integer between 1 and 10, where 1 is minimal confidence and 10 is maximal confidence. You should list your response in the Python dictionary format. After you have determined these things, provide a summary of the discussion topics during the transcript, and what words might be missed during transcription of the underlying audio file (technical terms, etc) based on your knowlege and which folder this transcript belongs in. This is intended for use by a speech-recognition model that accepts a system prompt. It should be less than 150 words.

The dictonary should be structured as followed:
I mean, I think the term for that is stereotypiIf the most likely directory is foo, and you have confidence 8, and you have generated a summary and term guide 'EXAMPLE SUMMARY TEXT', you should output:
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
	sorting_prompt += "\nEND OF TRANSCRIPT. Output the directory this transcript belongs in using the dictonary format I designated earlier."
	response_text = None
	import ast
	while response_text == None:
		try:
			response_text = (ollama_chat(sorting_prompt))
			response_text = re.search("{[^}]+}", response_text).group()
			response_text = ast.literal_eval(response_text)
			if (response_text["directory_name"]) not in transcript_dirs:
				response_text = None
				continue
			if "summary" not in response_text:
				response_text = None
				continue
		except:
			print(response_text)
			response_text = None
			continue
	return(response_text)
"""

	while response_text == None:
		import ast
		response_text = (ollama_chat(sorting_prompt))
		print(response_text)
		
		try:
			response_text = re.search("{[^}]+}", response_text).group()
			print(response_text)
			response_text = ast.literal_eval(response_text)
			
			if response_text["directory_name"] not in transcript_dirs:
                        	response_text = None
                        	continue
		except:
			continue
"""

#file = open("Consulting_transcripts_07-16-2026-19-46.txt")
#sort_transcript(file.read()[:5000])	
def write_transcript(filename="Beverly 7:2:26.m4a", folder="Consulting_transcripts", audio_folder = "Consulting_audio"):
	model = load("mlx-community/parakeet-tdt-0.6b-v2")

	sentence_start = None
	sentence_end = None

	result =  model.generate(filename, chunk_duration=300.0, overlap_duration = 15.0, context="AGI")
	total_gap = 0

	for sentence in result.sentences:
		sentence_start = sentence.start
		if sentence_end is not None:
			gap = (sentence_start - sentence_end)
			if gap < 0: gap = 0
			total_gap += gap
		sentence_end = sentence.end
		total_gap = total_gap / len(result.sentences)

		sentence_start = None
		sentence_end = None

	fulltext = ""
	for sentence in result.sentences:
		fulltext += (sentence.text)
		fulltext += ("\n")
		sentence_start = sentence.start
		if sentence_end is not None:
			gap = (sentence_start - sentence_end)
			if gap < 0: gap = 0
			if gap > 0.5:
				fulltext += ("\n")
		sentence_end = sentence.end
	filestat = os.stat(filename)
	import gc
	import mlx.core as mx
	del model
	gc.collect()
	mx.clear_cache()

	response_text = sort_transcript(fulltext)
	print(response_text)	
	qwen_text = qwen_transcribe(filename, response_text["summary"])
	
	folderroot = re.sub(r"_.+","", response_text["directory_name"])
	filewrite = folderroot + "_" + datetime.datetime.fromtimestamp(filestat.st_birthtime).strftime("%m-%d-%Y-%H-%M") + ".txt"
	transcripts = folderroot + "_transcripts"
	audio = folderroot + "_audio"
	with open(f"{transcripts}/{filewrite}", "w") as text:
		text.write(qwen_text)
	shutil.move(filename, f"{audio}/{filename}")
	print(filewrite)


	
for item in list_audio():
	write_transcript(item)
