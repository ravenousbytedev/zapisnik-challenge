# Zapisnik

A tool that reads a messy meeting transcript and works out who was there, what was decided, and who has to do what by when.

## Getting started

### Dependencies

Check `requirements.txt` for the required Python packages.

### Environment setup

This script requires an API key from OpenRouter, as well as a model ID. Check `.env.example` for more information.

### Usage

```sh
python3 zapisnik.py transcript.txt --out output/
```

## Output

In the above example, the script will output a `zapisnik.json` file and a `zapisnik.md` file under `output/transcript/`.

### JSON format

The JSON will contain the following data extracted from the transcript in Bosnian: the meeting title, date, location, attendees, absent people, topics, decisions, action items and open questions. Here's an example:

```json
{
    "title": "SASTANAK SAVJETA MJESNE ZAJEDNICE \"BRIJEG\"",
    "date": "2026-10-03",
    "location": "prostorije MZ Brijeg",
    "attendees": [
        {
            "name": "Amra Hod\u017ei\u0107",
            "role": null
        },
        {
            "name": "Kenan Mehi\u0107",
            "role": null
        },
        {
            "name": "Selma Kova\u010d",
            "role": null
        },
        {
            "name": "Zijad Begi\u0107",
            "role": null
        },
        {
            "name": "Mirza Ali\u0107",
            "role": null
        }
    ],
    "absent": [],
    "topics": [
        "dje\u010dije igrali\u0161te u parku",
        "rasvjeta u Ulici branilaca",
        "akcija \u010di\u0161\u0107enja obale rijeke"
    ],
    "decisions": [
        {
            "text": "Odluka da se prikupe jo\u0161 dvije ponude za opremu dje\u010dijeg igrali\u0161ta prije dono\u0161enja kona\u010dne odluke.",
            "lines": [
                10,
                11,
                12,
                13,
                14
            ]
        },
        {
            "text": "Odluka da se po\u0161alje zvani\u010dni dopis op\u0107ini u vezi sa neispravnom rasvjetom u Ulici branilaca; Selma Kova\u010d \u043f\u0438\u0448\u0435 dopis do ponedjeljka, Amra Hod\u017ei\u0107 ga potpisuje, a Mirza Ali\u0107 \u0161alje fotografije.",
            "lines": [
                19,
                20,
                21,
                22,
                23
            ]
        },
        {
            "text": "Odluka da se akcija \u010di\u0161\u0107enja obale rijeke odr\u017ei u subotu, 24. oktobra 2026. u 10 sati; Mirza Ali\u0107 nabavlja vre\u0107e i rukavice, a Kenan Mehi\u0107 obavje\u0161tava \u0161kolu i d\u017eemat.",
            "lines": [
                24,
                25,
                26,
                27,
                28
            ]
        }
    ],
    "action_items": [
        {
            "description": "Prikupljanje jo\u0161 dvije ponude za opremu dje\u010dijeg igrali\u0161ta i slanje na mail",
            "owner": "Kenan Mehi\u0107",
            "due_date": "2026-10-09",
            "due_original": "do petka",
            "confident": true,
            "note": null,
            "lines": [
                13,
                14
            ]
        },
        {
            "description": "Napisati zvani\u010dni dopis op\u0107ini o neispravnoj rasvjeti u Ulici branilaca",
            "owner": "Selma Kova\u010d",
            "due_date": "2026-10-05",
            "due_original": "do ponedjeljka",
            "confident": true,
            "note": null,
            "lines": [
                19,
                20
            ]
        },
        {
            "description": "Poslati fotografije neispravne rasvjete Selmi Kova\u010d",
            "owner": "Mirza Ali\u0107",
            "due_date": "2026-10-03",
            "due_original": "ve\u010deras",
            "confident": true,
            "note": null,
            "lines": [
                22,
                23
            ]
        },
        {
            "description": "Oka\u010diti obavijest o akciji \u010di\u0161\u0107enja do kraja sedmice",
            "owner": "Kenan Mehi\u0107",
            "due_date": "2026-10-09",
            "due_original": "do kraja sedmice",
            "confident": true,
            "note": null,
            "lines": [
                29
            ]
        },
        {
            "description": "Nabaviti vre\u0107e i rukavice za akciju \u010di\u0161\u0107enja",
            "owner": "Mirza Ali\u0107",
            "due_date": null,
            "due_original": null,
            "confident": false,
            "note": "Rok nije naveden u prepisu",
            "lines": [
                28
            ]
        },
        {
            "description": "Obavjestiti \u0161kolu i d\u017eemat o akciji \u010di\u0161\u0107enja",
            "owner": "Kenan Mehi\u0107",
            "due_date": null,
            "due_original": null,
            "confident": false,
            "note": "Rok nije naveden u prepisu",
            "lines": [
                28
            ]
        }
    ],
    "open_questions": [
        {
            "text": "Ko \u0107e finansirati nabavku vre\u0107a i rukavica za akciju \u010di\u0161\u0107enja?",
            "lines": [
                30,
                31
            ]
        }
    ]
}
```

Check `output/` for more examples.

### Markdown format

The Markdown will be a readable version of all the data contained in the JSON output. Check `output/` for examples.

## Approach

My approach to this challenge was to use an LLM with a strict system prompt to process the given transcript and extract all required data. The reason I chose this approach is because it's quick and relatively easy to implement programmatically, which was ideal for the relatively short time window I had to work on this project.

The major flaw of this approach is that the accuracy of the script depends heavily on the quality of the LLM used. For example, the model I initially used, Qwen 3.8 27B, would mess up line numbers all the time and also throw in random gibberish at times. At a few rare occasions, it would even hallucinate names. However, switching to the notably more powerful NVIDIA Nemotron 3 Ultra 550B immediately showed far better results.

### How I used AI assistants

I used ChatGPT to help weigh the pros and cons of different approaches to this problem and ultimately decided to settle for the LLM approach. I also used it later to help me rewrite my system prompt from an extensive and exhaustive but unorganized instruction set into a structured and very strict ruleset for the LLM. Apart from that, I only used official docs (e.g. for the `argparse` Python library and the LLM API), online forums (StackOverflow) and my own knowledge.

### What I would add with one more week

I would mainly work on a website for the script and a server with Node.js or Next.js to run everything on. Other than that, I would look into creating an additional script component that automatically tests the accuracy of the script and reports it alongside the extracted data for reference.
