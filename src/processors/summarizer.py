from transformers import pipeline, BartTokenizer
import os
import glob

from src.utils import setup_logger

class Summarizer:
    def __init__(self, model_name="facebook/bart-large-cnn"):
        self.logger = setup_logger('summarizer')
        self.model_name = model_name
        self.logger.info(f"Initializing summarizer with model: {model_name}")
        
        # Initialize the tokenizer and summarizer
        self.tokenizer = BartTokenizer.from_pretrained(model_name)
        self.summarizer_pipeline = pipeline("summarization", model=model_name)
        
    def summarize_text(self, text, max_input_length=1024, max_output_length=800, min_output_length=150):
        """Summarize a text string using the BART model"""
        try:
            # Ensure the text is not empty
            if not text.strip():
                self.logger.error("Cannot summarize empty text")
                return None
                
            # Tokenize and truncate the text to the maximum length
            inputs = self.tokenizer(text, max_length=max_input_length, truncation=True, return_tensors="tf")
            
            # Generate the summary
            summary_ids = self.summarizer_pipeline.model.generate(
                inputs["input_ids"], 
                max_length=max_output_length, 
                min_length=min_output_length,
                do_sample=False
            )
            
            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return summary
            
        except Exception as e:
            self.logger.error(f"Error summarizing text: {str(e)}", exc_info=True)
            raise
            
    def summarize_file(self, file_path, output_path=None):
        """Summarize text from a file and optionally save to another file"""
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file {file_path} does not exist.")
                
            # Read the article text from the file
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
                
            # Generate summary
            summary = self.summarize_text(text)
            
            # If output path is provided, save the summary
            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as file:
                    file.write(summary)
                self.logger.info(f"Summary written to {output_path}")
                
            return summary
                
        except Exception as e:
            self.logger.error(f"Error summarizing file {file_path}: {str(e)}", exc_info=True)
            raise
            
    def summarize_directory(self, input_dir, output_dir=None):
        """Summarize all markdown files in a directory"""
        try:
            # Create output directory if specified
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            # Find all markdown files
            markdown_files = glob.glob(os.path.join(input_dir, "*.md"))
            
            results = {
                "processed": 0,
                "failed": 0,
                "files": []
            }
            
            for md_file in markdown_files:
                try:
                    file_name = os.path.basename(md_file)
                    base_name = os.path.splitext(file_name)[0]
                    
                    # Determine output path if needed
                    output_path = None
                    if output_dir:
                        output_path = os.path.join(output_dir, f"{base_name}_summary.txt")
                        
                    # Summarize the file
                    summary = self.summarize_file(md_file, output_path)
                    
                    results["processed"] += 1
                    results["files"].append({
                        "input": md_file,
                        "output": output_path,
                        "success": True
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing {md_file}: {str(e)}")
                    results["failed"] += 1
                    results["files"].append({
                        "input": md_file,
                        "error": str(e),
                        "success": False
                    })
                    
            self.logger.info(f"Summarization completed. Processed: {results['processed']}, Failed: {results['failed']}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error summarizing directory {input_dir}: {str(e)}", exc_info=True)
            raise


def summarize_file(file_path, output_path=None):
    """Helper function to summarize a single file"""
    summarizer = Summarizer()
    return summarizer.summarize_file(file_path, output_path)
    
def summarize_directory(input_dir, output_dir=None):
    """Helper function to summarize all files in a directory"""
    summarizer = Summarizer()
    return summarizer.summarize_directory(input_dir, output_dir)