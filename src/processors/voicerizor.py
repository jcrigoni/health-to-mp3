#!/usr/bin/env python3
# Voicerizor - Convert markdown documents to MP3 files

import os
import glob
import argparse
import uuid
import logging
from pathlib import Path
import subprocess
from kokoro import KPipeline
import soundfile as sf
import torch
import numpy as np
from pydub import AudioSegment
import sys

# Add parent directory to system path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

logger = setup_logger('voicerizor')

class TextToSpeechProcessor:
    """Process markdown files to audio using Kokoro TTS engine"""
    
    def __init__(self, lang_code='f', voice='ff_siwis', output_dir=None):
        """
        Initialize the TTS processor
        
        Args:
            lang_code (str): Language code ('f' for French, 'a' for American English, etc.)
            voice (str): Voice model to use
            output_dir (str): Directory to save audio files
        """
        self.lang_code = lang_code
        self.voice = voice
        
        # Create pipeline
        logger.info(f"Initializing Kokoro pipeline with lang_code={lang_code}")
        self.pipeline = KPipeline(lang_code=lang_code)
        
        # Set output directory
        if output_dir:
            self.output_dir = output_dir
        else:
            # Create timestamped output directory if none provided
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = os.path.join(os.getcwd(), f"audio_output_{timestamp}")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Audio files will be saved to {self.output_dir}")
    
    def process_markdown_file(self, md_file_path):
        """
        Process a markdown file and convert it to audio
        
        Args:
            md_file_path (str): Path to the markdown file
            
        Returns:
            str: Path to the generated MP3 file
        """
        logger.info(f"Processing markdown file: {md_file_path}")
        
        # Get the UUID from the filename (removing .md extension)
        file_uuid = Path(md_file_path).stem
        
        # Create a temporary directory for the WAV files
        temp_dir = os.path.join(self.output_dir, f"temp_{file_uuid}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Read the markdown file
        with open(md_file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        # Generate audio files from text
        logger.info(f"Generating audio for {file_uuid}")
        generator = self.pipeline(text, voice=self.voice)
        
        wav_files = []
        for i, (gs, ps, audio) in enumerate(generator):
            # Save each sentence as a separate WAV file
            wav_file = os.path.join(temp_dir, f"{i:04d}.wav")
            sf.write(wav_file, audio, 24000)
            wav_files.append(wav_file)
        
        # Concatenate all WAV files into a single MP3 file
        mp3_path = os.path.join(self.output_dir, f"{file_uuid}.mp3")
        self._concatenate_and_convert(wav_files, mp3_path)
        
        # Clean up temporary files
        for wav_file in wav_files:
            os.remove(wav_file)
        os.rmdir(temp_dir)
        
        return mp3_path
    
    def _concatenate_and_convert(self, wav_files, output_mp3_path):
        """
        Concatenate multiple WAV files into a single MP3 file
        
        Args:
            wav_files (list): List of WAV file paths
            output_mp3_path (str): Output MP3 file path
        """
        logger.info(f"Concatenating {len(wav_files)} audio segments and converting to MP3")
        
        # Use pydub to concatenate the audio files
        combined = AudioSegment.empty()
        for wav_file in wav_files:
            audio = AudioSegment.from_wav(wav_file)
            combined += audio
        
        # Export as MP3
        combined.export(output_mp3_path, format="mp3", bitrate="192k")
        logger.info(f"Saved MP3 file to {output_mp3_path}")


def process_directory(input_dir, output_dir=None, lang_code='f', voice='ff_siwis'):
    """
    Process all markdown files in a directory
    
    Args:
        input_dir (str): Directory containing markdown files
        output_dir (str): Directory to save audio files
        lang_code (str): Language code
        voice (str): Voice model to use
        
    Returns:
        list: Paths to the generated MP3 files
    """
    # Initialize the processor
    processor = TextToSpeechProcessor(lang_code=lang_code, voice=voice, output_dir=output_dir)
    
    # Find all markdown files
    md_files = glob.glob(os.path.join(input_dir, "*.md"))
    logger.info(f"Found {len(md_files)} markdown files in {input_dir}")
    
    # Process each file
    mp3_files = []
    for md_file in md_files:
        try:
            mp3_path = processor.process_markdown_file(md_file)
            mp3_files.append(mp3_path)
        except Exception as e:
            logger.error(f"Error processing {md_file}: {str(e)}")
    
    return mp3_files


if __name__ == "__main__":
    import datetime
    
    parser = argparse.ArgumentParser(description="Convert markdown files to MP3 audio files")
    parser.add_argument(
        "--input", "-i", 
        default="data", 
        help="Input directory containing markdown files (default: data)"
    )
    parser.add_argument(
        "--output", "-o", 
        default=None, 
        help="Output directory for MP3 files (default: auto-generated timestamp directory)"
    )
    parser.add_argument(
        "--lang", "-l", 
        default="f", 
        help="Language code: 'f' for French, 'a' for American English, 'b' for British English, 'z' for Mandarin (default: f)"
    )
    parser.add_argument(
        "--voice", "-v", 
        default="ff_siwis", 
        help="Voice model to use (default: ff_siwis)"
    )
    
    args = parser.parse_args()
    
    if not args.output:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"audio_output_{timestamp}"
    
    # Process all markdown files in the directory
    mp3_files = process_directory(
        args.input, 
        args.output, 
        lang_code=args.lang, 
        voice=args.voice
    )
    
    logger.info(f"Successfully generated {len(mp3_files)} MP3 files")