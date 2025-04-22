from transformers import AutoTokenizer, MarianMTModel
import os
import glob

from src.utils import setup_logger

class Translator:
    def __init__(self, model_name="Helsinki-NLP/opus-mt-en-zh"):
        self.logger = setup_logger('translator')
        self.model_name = model_name
        self.logger.info(f"Initializing translator with model: {model_name}")
        
        # Initialize the model and tokenizer
        self.model = MarianMTModel.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
    def _chunk_text(self, text, max_length=500):
        """Split the text into chunks of a maximum length."""
        words = text.split()
        for i in range(0, len(words), max_length):
            yield ' '.join(words[i:i + max_length])
            
    def translate_text(self, text, source_lang=None, target_lang=None):
        """Translate a text string using the MarianMT model"""
        try:
            # Ensure the text is not empty
            if not text.strip():
                self.logger.error("Cannot translate empty text")
                return None
                
            # Split the text into chunks
            chunks = list(self._chunk_text(text))
            
            translations = []
            for chunk in chunks:
                model_inputs = self.tokenizer(chunk, return_tensors="pt", padding=True, truncation=True)
                gen_tokens = self.model.generate(
                    **model_inputs, 
                    num_beams=5,  # Use beam search with 5 beams
                    no_repeat_ngram_size=2  # Prevent repeating 2-grams
                )
                translation = self.tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)
                translations.append(translation[0])
            
            # Combine the translations
            full_translation = "\n".join(translations)
            return full_translation
            
        except Exception as e:
            self.logger.error(f"Error translating text: {str(e)}", exc_info=True)
            raise
            
    def translate_file(self, file_path, output_path=None):
        """Translate text from a file and optionally save to another file"""
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file {file_path} does not exist.")
                
            # Read the text from the file
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
                
            # Generate translation
            translation = self.translate_text(text)
            
            # If output path is provided, save the translation
            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as file:
                    file.write(translation)
                self.logger.info(f"Translation written to {output_path}")
                
            return translation
                
        except Exception as e:
            self.logger.error(f"Error translating file {file_path}: {str(e)}", exc_info=True)
            raise
            
    def translate_directory(self, input_dir, output_dir=None, file_pattern="*.md"):
        """Translate all matching files in a directory"""
        try:
            # Create output directory if specified
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            # Find all matching files
            input_files = glob.glob(os.path.join(input_dir, file_pattern))
            
            results = {
                "processed": 0,
                "failed": 0,
                "files": []
            }
            
            for input_file in input_files:
                try:
                    file_name = os.path.basename(input_file)
                    base_name = os.path.splitext(file_name)[0]
                    
                    # Determine output path if needed
                    output_path = None
                    if output_dir:
                        output_path = os.path.join(output_dir, f"{base_name}_translated.txt")
                        
                    # Translate the file
                    translation = self.translate_file(input_file, output_path)
                    
                    results["processed"] += 1
                    results["files"].append({
                        "input": input_file,
                        "output": output_path,
                        "success": True
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing {input_file}: {str(e)}")
                    results["failed"] += 1
                    results["files"].append({
                        "input": input_file,
                        "error": str(e),
                        "success": False
                    })
                    
            self.logger.info(f"Translation completed. Processed: {results['processed']}, Failed: {results['failed']}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error translating directory {input_dir}: {str(e)}", exc_info=True)
            raise


def translate_file(file_path, output_path=None):
    """Helper function to translate a single file"""
    translator = Translator()
    return translator.translate_file(file_path, output_path)
    
def translate_directory(input_dir, output_dir=None, file_pattern="*.md"):
    """Helper function to translate all files in a directory"""
    translator = Translator()
    return translator.translate_directory(input_dir, output_dir, file_pattern)