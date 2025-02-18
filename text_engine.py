from transformers import pipeline, BartTokenizer
import os

# Initialize the tokenizer and summarizer
tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

file_path = "output_data_2025_02_15_122603/e723b364-9ad8-4c0d-b396-58be3c8e0ea7.md"

# Check if the file exists
if not os.path.exists(file_path):
    raise FileNotFoundError(f"The file {file_path} does not exist.")

# Read the article text from a file
with open(file_path, "r", encoding="utf-8") as file:
    ARTICLE = file.read()

# Ensure the article is not empty
if not ARTICLE.strip():
    raise ValueError("The article text is empty.")

# Tokenize and truncate the article to the maximum length
inputs = tokenizer(ARTICLE, max_length=1024, truncation=True, return_tensors="tf")

# Generate the summary
summary_ids = summarizer.model.generate(inputs["input_ids"], max_length=800, min_length=150, do_sample=False)
summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# Write the summary to a .txt file
with open("summary2.txt", "w", encoding="utf-8") as file:
    file.write(summary)

print("Summary written to summary.txt")
