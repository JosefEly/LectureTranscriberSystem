from mlx_audio.stt import load
#mlx-community/parakeet-tdt-0.6b-v3
# Load the multilingual v3 model
model = load("mlx-community/parakeet-tdt-0.6b-v2")

sentence_start = None
sentence_end = None

result =  model.generate("Beverly.m4a", chunk_duration=300.0, overlap_duration = 15.0)
total_gap = 0

for sentence in result.sentences:
	print(sentence.text)
	sentence_start = sentence.start
	if sentence_end is not None:
		gap = (sentence_start - sentence_end)
		if gap < 0: gap = 0
		if gap > 0.5:
			print("\n")
		total_gap += gap
	sentence_end = sentence.end

print(total_gap/len(result.sentences))
