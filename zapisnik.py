import argparse
import datetime
import dotenv
import json
import os
import pathlib
import requests

INSTRUCTIONS = """
You are an automated minute-taker service, and you have to strictly follow all rules declared below.
Your task is to read a messy meeting transcript and work out who was there, what was decided, and who has to do what by when.
From each transcript, you should extract:
- Basic info: meeting title, date, and place or platform
- Attendees and absentees: full name, and role if mentioned
- Topics: the agenda items that were discussed
- Decisions: only what was actually decided, and only the final version
- Action items: what needs to be done, who owns it, and the deadline (as a real date)
- Open questions: things that were raised but not resolved
Remember to not invent information - if a certain piece of information is too ambiguous or completely unavailable, don't invent it, and instead put `null` instead of a string.
In the case of relative time specifications ("by Friday", "tonight", "tomorrow"), you are required to use the time of the transcript to figure out the exact time specified.
In the case of the transcript being raw and without names, you are required to figure out the name of each speaker from the context of the conversation itself.
Be careful here, as errors are unacceptable and can completely mess everything up.
In the case of obvious roles (e.g. members of a committee in a committee-only meeting), put `null` on every attendee who doesn't have a special role (e.g. a committee member), and only specify special roles (e.g. the committee president).
Never assume roles - rather put `null` instead of giving misinformation.
Do not put stuff like "likely" or "probably" next to roles - it creates unnecessary misunderstanding.
Transcripts will be mostly in Bosnian, but can also be a mix of Bosnian and English.
For Bosnian, you are required to restore diacritics (e.g. "c" into "č" or "ć", depending on the word, "s" into "š", "z" into "ž" and "dj" into "đ").
All textual information in the extracted data must be in Bosnian (Latin, not Cyrillic), translated from English in the case of mixed languages.
You are also required to restore all punctuation and fix any grammar errors in the text, and do not make any errors yourself.
You can also interpret the text as Croatian when possible if it's easier for you to understand, but never under any circumstances should you use Croatian in the text reconstruction.
Deliver the extracted data in a JSON format.
The exact fields that your JSON must contain are:
- "title"
- "date"
- "location"
- "attendees"
- "absent"
- "topics"
- "decisions"
- "action_items"
- "open_questions"
The "title" and "date" fields are strings.
The "location" field is a string that specifies the physical location of the meeting, or, in the case of a virtual meeting, the platform it was held on.
In the case of an unspecified physical location or platform, just put `null`.
"attendees" is an array containing information about every present person, and each entry has to be an object with the following fields:
- "name"
- "role"
"name" and "role" are both strings representing the name and the role of the attendee, respectively.
Do not include absent people in "attendees" - they belong in the "absent" field only.
"absent" is an array containing the names about every absent person, and each entry is just a string - the name of the absent person.
"topics" is another array of strings, containing the topics mentioned on the meeting.
"decisions" is an array containing information about decisions made on the meeting.
As specified before, it should only contain final and confirmed decisions.
Each entry should be an object with the following fields:
- "text"
- "lines"
"text" is the information about the decision, and "lines" is an array containing the line numbers of the lines which contributed to the confirmation of the decision.
"action_items" is an array where every entry must be an object with the following fields:
- "description"
- "owner"
- "due_date"
- "due_original"
- "confident"
- "note"
- "lines"
"description" is a string describing the action item, and is always in infinitive form without end punctuation, and "owner" is a string representing the name of the person who is tasked with the action.
"due_date" is the due date of the action, whereas "due_original" is the exact wording from the meeting transcript (e.g. "by Friday").
"confident" is a boolean value that, when false, means the deadline is ambiguous.
If "confident" is false, "note" is a string that specifies why the deadline is ambiguous; otherwise, "note" must be `null`.
"lines", just like for "decisions" fields, is an array of line numbers.
Finally, "open_questions" is an array containing information about still open questions.
Each entry should be an object with the following fields:
- "text"
- "lines"
"text" is the question itself, and it must be in interrogative form, and "lines" is an array of line numbers.
"lines" must always be an array of numbers in every use case.
Do not under any circumstance place additional notes for open questions (e.g. "will be discussed next meeting").
All dates are specified in YYYY-MM-DD format.
Never put any dates in "text", "description" or "note" fields.
Don't you DARE use "null" as a string when specifying unknown information - always use the JSON keyword `null`.
Do not add any text before or after the JSON you process - no "Okay, here's your JSON" or "If you need anything else, I'm here to help" - just the JSON and that's it.
The result of your work is very important, so make sure to try your best.
"""

def take_minutes(transcript, /):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json={
            "model": os.getenv("GROQ_MODEL_ID"),
            "messages": [
                {
                    "role": "system",
                    "content": INSTRUCTIONS
                },
                {
                    "role": "user",
                    "content": f"```\n{transcript}```"
                }
            ]
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv("GROQ_API_KEY")}"
        }
    )
    if not response.ok:
        raise Exception(response.text)
    return json.loads(
        (lambda s: s.replace("\"null\"", "null"))
        (response.json()["choices"][0]["message"]["content"])
    )

def write_md(file, data, /):
    def cvt_date(date, /):
        return datetime.datetime.strftime(datetime.datetime.strptime(date, "%Y-%m-%d"), "%d. %m. %Y.")
    def make_lines_text(lines, /):
        return (
            ""
            if not lines else
            f"{lines[0]}"
            if len(lines) == 1 else
            f"{lines[0]}-{lines[-1]}"
        )
    file.write(
        f"# {data["title"]} ({data["location"]}, {cvt_date(data["date"])})\n\n" +
        "### Prisutni\n\n"
    )
    for attendee in data["attendees"]:
        file.write(
            f"- {attendee["name"]}" +
            f"{f" ({attendee["role"]})" if attendee["role"] else ""}\n\n"
        )
    if data["absent"]:
        file.write(f"### Odsutni\n\n")
        for name in data["absent"]:
            file.write(f"- {name}\n\n")
    file.write(f"### Teme\n\n")
    for topic in data["topics"]:
        file.write(f"- {topic}\n\n")
    file.write(f"### Odluke\n\n| Odluka | Linije |\n|-|-|\n")
    for decision in data["decisions"]:
        file.write(f"| {decision["text"]} | {make_lines_text(decision["lines"])} |\n")
    file.write(
        f"\n### Zaduženja\n\n| Opis | Osoba | Krajnji rok | Dodatna napomena | Linije |" +
        "\n|-|-|-|-|-|\n"
    )
    for action_item in data["action_items"]:
        file.write(
            f"| {action_item["description"]} | {action_item["owner"]} " +
            f"| {
                "?"
                if action_item["due_date"] is None else
                f"{cvt_date(action_item["due_date"])} (\"{action_item["due_original"]}\")"
            }" +
            f"| {("" if action_item["confident"] else action_item["note"])} " +
            f"| {make_lines_text(action_item["lines"])} |\n"
        )
    file.write("\n### Otvorena pitanja\n\n| Pitanje | Linije |\n|-|-|\n")
    for open_questions in data["open_questions"]:
        file.write(f"| {open_questions["text"]} | {make_lines_text(open_questions["lines"])} |\n")

def main():
    dotenv.load_dotenv()
    parser = argparse.ArgumentParser(
        prog="python3 zapisnik.py",
        description=(
            "A tool that reads a messy meeting transcript and works out who was there, " +
            "what was decided, and who has to do what by when."
        )
    )
    parser.add_argument("FILENAME")
    parser.add_argument("--out", default="output/", type=pathlib.Path)
    namesp = parser.parse_args()
    with open(namesp.FILENAME) as file:
        data = take_minutes(file.read())
        file.close()
    if not os.path.exists(namesp.out):
        os.mkdir(namesp.out)
    elif not os.path.isdir(namesp.out):
        raise NotADirectoryError(namesp.out)
    dir = f"{namesp.out}/{os.path.splitext(os.path.basename(namesp.FILENAME))[0]}"
    if not os.path.exists(dir):
        os.mkdir(dir)
    elif not os.path.isdir(dir):
        raise NotADirectoryError(dir)
    with open(f"{dir}/zapisnik.json", "w+") as file:
        json.dump(data, file, indent=4)
        file.close()
    with open(f"{dir}/zapisnik.md", "w+") as file:
        write_md(file, data)
        file.close()

if __name__ == "__main__":
    main()
