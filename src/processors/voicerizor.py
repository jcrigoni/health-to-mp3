# Initalize a pipeline
from kokoro import KPipeline
import soundfile as sf
import torch
import numpy as np
'''
🇺🇸 'a' => American English, 🇬🇧 'b' => British English
🇪🇸 'e' => Spanish es
🇫🇷 'f' => French fr-fr
🇮🇳 'h' => Hindi hi
🇮🇹 'i' => Italian it
🇯🇵 'j' => Japanese: pip install misaki[ja]
🇧🇷 'p' => Brazilian Portuguese pt-br
🇨🇳 'z' => Mandarin Chinese: pip install misaki[zh]
'''
pipeline = KPipeline(lang_code='f') # <= make sure lang_code matches voice, reference above.

# This text is for demonstration purposes only, unseen during training
text = '''
Le dromadaire resplendissant déambulait tranquillement. Dans les méandres en mastiquant de petites feuilles vernissées. 
Le grand chêne majestueux se penchait sur cette rivière sourde aux plaintes des rochers grinçants sous le poids des flots interminables. 
La colonne de fumée s'échappait lentement du volcan asmathique occultant le ciel du sud d'où vient d'habitude cette douce lumière jaune.
'''

# Generate and save audio files in a loop.
generator = pipeline(
    text, voice='ff_siwis')

for i, (gs, ps, audio) in enumerate(generator):
    # print(i, gs, ps)
    sf.write(f'{i}.wav', audio, 24000)