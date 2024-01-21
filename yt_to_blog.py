
import openai
import os
import re
import sys
import logging
from pytube import YouTube
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from datetime import datetime

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to open a file and return its contents as a string
def open_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as infile:
            return infile.read()
    except Exception as e:
        logging.error(f"Error reading file {filepath}: {e}")
        return None

# Function to save content to a file
def save_file(filepath, content):
    try:
        with open(filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(content)
    except Exception as e:
        logging.error(f"Error saving to file {filepath}: {e}")

def chatgpt(api_key, model, prompt, temperature=0.7, frequency_penalty=0.2, presence_penalty=0):
    try:
        openai.api_key = api_key
        conversation = []  # Initialize an empty conversation history
        conversation.append({"role": "user", "content": prompt})
        completion = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            messages=conversation)
        chat_response = completion['choices'][0]['message']['content']
        return chat_response
    except Exception as e:
        logging.error(f"Error in chatGPT call: {e}")
        return None

# Function to extract rating from a string
def extract_rating(rating_str):
    if rating_str:
        match = re.search(r'(\d+)/100', rating_str)
        if match:
            return int(match.group(1))
    return None

# Function to generate improvement suggestions
def generate_improvement_instructions(api_key, model, draft):
    try:
        improvement_prompt = open_file('improvement_prompt.txt').replace("<<DRAFT>>", draft)
        if improvement_prompt:
            instructions = chatgpt(api_key, model, improvement_prompt)
            return instructions
        return None
    except Exception as e:
        logging.error(f"Error generating improvement instructions: {e}")
        return None

# Function to download YouTube video
def download_youtube_video(url):
    try:
        youtube_video = YouTube(url)
        video = youtube_video.streams.get_highest_resolution()
        filename = "temp_video.mp4"
        video.download(filename=filename)
        return filename
    except Exception as e:
        logging.error(f"Failed to download YouTube video: {e}")
        return None

# Function to convert video to MP3
def convert_video_to_mp3(video_path):
    try:
        video = VideoFileClip(video_path)
        audio = video.audio
        audio_filename = video_path.replace('.mp4', '.mp3')
        audio.write_audiofile(audio_filename)
        return audio_filename
    except Exception as e:
        logging.error(f"Error converting video to MP3: {e}")
        return None

# Main function to orchestrate the script's workflow
def main(url):
    api_key = os.getenv('OPENAI_API_KEY')
    model_name = "gpt-4-0613"

    # Initialize folder for saving data
    if not os.path.exists('data'):
        os.mkdir('data')

    # Download YouTube video
    video_path = download_youtube_video(url)
    if video_path is None:
        logging.error("Failed to download video.")
        return

    # Convert video to MP3
    audio_path = convert_video_to_mp3(video_path)
    if audio_path is None:
        logging.error("Failed to convert video to MP3.")
        return

    # Initialize the draft
    initial_draft = "Your initial draft content here."

    # Evaluate the initial draft
    evaluation_prompt = open_file('prompt1.txt').replace("<<ANSWER>>", initial_draft)
    rating = chatgpt(api_key, model_name, evaluation_prompt)
    if rating is None:
        logging.error("Failed to evaluate initial draft.")
        return

    extracted_rating = extract_rating(rating)
    logging.info(f"Initial rating: {extracted_rating}")

    # Refine the draft
    new_draft = initial_draft
    while extracted_rating is None or extracted_rating < 90:
        improvement_instructions = generate_improvement_instructions(api_key, model_name, new_draft)
        if improvement_instructions is None:
            logging.error("Failed to generate improvement instructions.")
            break

        new_prompt = f"Please improve the following draft based on the provided suggestions.

                        Original Draft:
                        {new_draft}

                        Improvement Suggestions:
                        {improvement_instructions}"
        new_draft = chatgpt(api_key, model_name, new_prompt)
        if new_draft is None:
            logging.error("Failed to generate new draft.")
            break

        evaluation_prompt = open_file('prompt1.txt').replace("<<ANSWER>>", new_draft)
        rating = chatgpt(api_key, model_name, evaluation_prompt)
        extracted_rating = extract_rating(rating)
        logging.info(f"Updated rating: {extracted_rating}")

    # Save the final answer
    save_file('data/final_output.txt', new_draft)
    logging.info("Final output saved in 'data/final_output.txt'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        main(url)
    else:
        logging.error("No URL provided.")
