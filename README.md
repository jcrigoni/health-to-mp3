# health-mp3
From scraping health blog to mp3 summary

## Project Description
This project scrapes health blogs for articles and converts them into audio summaries in MP3 format. It aims to make health information more accessible by providing audio versions of written content.

## Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/jcrigoni/health-to-mp3.git/
    ```
2. Navigate to the project directory:
    ```sh
    cd health-to-mp3
    ```
3. Install the required dependencies:
    ```sh
    pipenv install --deploy
    ```

## Usage
1. Run the scraper to collect articles:
    ```sh
    python scraper_engine.py
    ```
2. Convert the scraped articles to MP3:
    ```sh
    python convert_to_mp3.py
    ```
3. Find the generated MP3 files in the `output` directory. (not yet)

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT Licence and Commons Clause.
