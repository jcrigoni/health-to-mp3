from transformers import AutoTokenizer, MarianMTModel
import os

model_name = "Helsinki-NLP/opus-mt-en-fr"
model = MarianMTModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

file_path = "output_data_2025_02_15_122603/e723b364-9ad8-4c0d-b396-58be3c8e0ea7.md"

# Read the article text from a file
with open(file_path, "r", encoding="utf-8") as file:
    ARTICLE = file.read()

def chunk_text(text, max_length):
    """Split the text into chunks of a maximum length."""
    words = text.split()
    for i in range(0, len(words), max_length):
        yield ' '.join(words[i:i + max_length])

# Split the article into chunks
chunks = list(chunk_text(ARTICLE, 500))  # Adjust the chunk size as needed

translations = []
for chunk in chunks:
    model_inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True)
    gen_tokens = model.generate(
        **model_inputs, 
        num_beams=5,  # Use beam search with 5 beams
        no_repeat_ngram_size=2  # Prevent repeating 2-grams
    )
    translation = tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)
    translations.append(translation[0])

# Combine the translations
full_translation = "\n".join(translations)

# Write the translation to a .txt file
with open("translation.txt", "w", encoding="utf-8") as file:
    file.write(full_translation)

print("Translation written to translation.txt")