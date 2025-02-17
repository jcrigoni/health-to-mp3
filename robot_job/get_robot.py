import requests
import os
from config_robot import ROBOT_CONFIG

# Create output directory if it doesn't exist
output_dir = 'output_robot'
os.makedirs(output_dir, exist_ok=True)

url = ROBOT_CONFIG['site__path']
response = requests.get(url)

if response.status_code == 200:
   # Construct the full file path using os.path.join
   filepath = os.path.join(output_dir, "robot.txt")
   
   with open(filepath, "w", encoding="utf-8") as file:
       file.write(response.text)
   print("✅ Robot.txt file saved successfully!")
else:
   print("The robots.txt file doesn't exist or access is forbidden.")