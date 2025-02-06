import requests

url = "https://healthline.com/robots.txt"
response = requests.get(url)

if response.status_code == 200:
    with open("robot.txt", "w", encoding="utf-8") as file:
        file.write(response.text)
    print("✅ Fichier robot.txt sauvegardé avec succès !")
else:
    print("Le fichier robots.txt n'existe pas ou l'accès est interdit.")