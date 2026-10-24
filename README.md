# Zapisnik

A tool that reads a messy meeting transcript and works out who was there, what was decided, and who has to do what by when.

## Getting started

### Dependencies

Check "requirements.txt" for the required Python packages.

### Environment setup

This script requires an API key from OpenRouter, as well as a model ID. Check ".env.example" for more information.

### Usage

```
python3 zapisnik.py <transcript filename> --out <output directory>
```

## Approach

My approach to this challenge was to use an LLM with a strict system prompt to process the given transcript and extract all required data. The reason I chose this approach is because it's quick and relatively easy to implement programmatically, which was ideal for the relatively short time window I had to work on this project.

The major flaw of this approach is that the accuracy of the script depends heavily on the quality of the LLM used. For example, the model I initially used, Qwen 3.8 27B, would mess up line numbers all the time and also throw in random gibberish at times. At a few rare occasions, it even hallucinated names. However, switching to the notably more powerful NVIDIA Nemotron 3 Ultra 550B immediately shower far better results.

### How I used AI assistants

I used ChatGPT to help weigh the pros and cons of different approaches to this problem and ultimately decided to settle for the LLM approach. I also used it later to help me rewrite my system prompt from an extensive and exhaustive but unorganized instruction set into a structured and very strict ruleset for the LLM. Apart from that, I only used official docs (e.g. for `argparse` Python library and the LLM API), online forums (StackOverflow) and my own knowledge.

### What I would add with one more week

I would love to work on a GUI for the program using a library like Tkinter or PyWin32, as well as a website for the script and a server with Node.js or Next.js to run everything on. Other than that, I would maybe try to create another script to automatically test the accuracy of the minute taker and report it alongside the extracted data for reference.
