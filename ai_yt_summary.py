#! /usr/bin/python3

import os
import sys
import re
import requests
import textwrap
import configparser
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
from openai import OpenAI


# Variable assignments and Usage instructions

load_dotenv()
if "OPENAI_API_KEY" not in os.environ:
    print('Error: OPENAI_API_KEY not found in environment variables.')
    sys.exit(1)
if len(sys.argv) < 2:
    print('Usage: python get_yt_summary.py <YouTube Video ID> <Prompt ID (optional)>')
    sys.exit(1)
video_id = sys.argv[1]
if os.path.isfile('prompts.ini'):
    prompt_id = sys.argv[2] if len(sys.argv) > 2 else '1' # Default to first prompt if not provided
else:
    prompt_id = 0
title_url = f'https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json'


# Functions

def load_prompts():
    '''
    Loads prompts from a configuration file.
    '''
    config = configparser.ConfigParser(allow_no_value=True)
    config.read('prompts.ini')
    prompts = {}
    for section in config.sections():
        body = "\n".join(line for line in config._sections[section])
        prompts[section] = body.strip()
    prompts['prompt 0'] = 'Please provide a summary of the following video transcript.'
    return prompts

def get_youtube_title(title_url):
    '''
    Gets the title of a YouTube video using its video ID via oEmbed.
    No API key required.
    '''
    resp = requests.get(title_url)
    resp.raise_for_status()  # raise exception if request failed
    data = resp.json()
    return data["title"]

def get_transcript(video_id):
    '''
    Returns the transcript of a YouTube video using its video ID.
    '''
    ytt_api = YouTubeTranscriptApi()
    ytt_lines = []
    for snippet in ytt_api.fetch(video_id):
        ytt_lines.append(snippet.text)
    return textwrap.fill(' '.join(ytt_lines), width=80)

def oai_summarize_ytt(prompt, ytt_fulltext):
    '''
    Asks the OpenAI API to summarize the provided transcript text.
    '''
    full_prompt = prompt + '\n\n' + ytt_fulltext
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5-mini",
        input=full_prompt
    )

    return response.output_text

def make_filename(yt_title):
    '''
    Creates a safe filename for the output text file.
    '''
    now = datetime.now()
    date_string = now.strftime("%Y%m%d%H%M%S")
    yt_title = re.sub(r'[^a-zA-Z0-9 ]', '', yt_title)[:30]
    outfile = f"{date_string}_{video_id}_{yt_title}.txt"
    outfile = outfile.replace(' ', '-')
    outfile = os.path.join('yt_summaries', outfile)
    return outfile

def save_file(outfile, yt_title, response_text, ytt_fulltext):
    '''
    Saves the summary and transcript to a text file.
    '''
    os.makedirs('yt_summaries', exist_ok=True)
    with open(outfile, 'w', encoding='utf-8') as fd:
        fd.write(yt_title + '\n\n')
        fd.write(response_text)
        fd.write('\n\n')
        fd.write(ytt_fulltext)

def main():
    prompts = load_prompts()
    yt_title = get_youtube_title(title_url)
    ytt_fulltext = get_transcript(video_id)
    prompt = prompts['prompt ' + str(prompt_id)] if 'prompt ' + str(prompt_id) in prompts else prompts['prompt 0']
    oai_response_text = oai_summarize_ytt(prompt, ytt_fulltext)
    outfile = make_filename(yt_title)
    save_file(outfile, yt_title, oai_response_text, ytt_fulltext)


# Main execution
    
if __name__ == "__main__":
    main()
