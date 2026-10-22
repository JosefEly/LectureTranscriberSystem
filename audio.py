from mlx_audio.stt import load
#mlx-community/parakeet-tdt-0.6b-v3
# Load the multilingual v3 model
import datetime
import shutil

# ['.txt', '.DS_Store', 'bin', 'Consulting_audio', 'include', 'Other', 'pyvenv.cfg', '..txt', 'Beverly 7:2:26.m4a', 'lib', 'audio.py', '.git', 'Consulting_transcripts', 'archived', 'Beverly.m4a', 'Allie Penam.m4a', 'share']


import os

def list_audio():
	file_list = os.listdir(os.getcwd())
	file_audio = []
	for item in file_list:
		if ".m4a" in item and item not in file_audio:
			file_audio.append(item)
	return (file_audio)

list_audio()
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
	print(fulltext)
	filestat = os.stat(filename)
	filewrite = folder + "_" + datetime.datetime.fromtimestamp(filestat.st_birthtime).strftime("%m-%d-%Y-%H-%M") + ".txt"
	with open(f"{folder}/{filewrite}", "w") as text:
		text.write(fulltext)
	shutil.move(filename, f"{audio_folder}/{filename}")
	print(filewrite)
	
for item in list_audio():
	write_transcript(item)
