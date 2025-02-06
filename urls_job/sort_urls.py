# Function to read, sort, and append URLs in a cleaner format
def sort_urls(input_file, output_file):
    try:
        # Open the input file and read all lines (URLs)
        with open(input_file, 'r') as file:
            urls = file.readlines()
        
        # Strip any leading/trailing whitespace and sort the URLs
        urls = [url.strip() for url in urls]
        urls.sort()

        # Append the sorted URLs in a cleaner format to the output file
        with open(output_file, 'a') as file:  # Open the file in append mode
            # Start the list and write each URL separated by a comma and a newline
            file.write("[\n")
            for url in urls:
                file.write(f"    '{url}',\n")  # Indentation for cleaner look
            file.write("]\n")  # End the list with a closing bracket

        print(f"URLs sorted and appended successfully! Check the file: {output_file}")
    
    except FileNotFoundError:
        print(f"Error: The file {input_file} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Specify input and output file paths
input_file = 'health_urls.txt'
output_file = 'sorted_health_urls.txt'

# Call the function
sort_urls(input_file, output_file)
