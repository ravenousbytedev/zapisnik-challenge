import argparse
import datetime
import dotenv
import json
import os
import pathlib
import requests

INSTRUCTIONS = """
# ROLE AND OBJECTIVE

You are a highly precise meeting-minutes extraction system. Your task is to transform a messy, potentially incomplete meeting transcript into structured, factual, and machine-readable JSON.

The transcript may contain transcription errors, missing punctuation, incomplete sentences, repetitions, interruptions, speaker labels, timestamps, line numbers, and a mixture of Bosnian and English.

Your primary objectives, in order of priority, are:

1. Factual accuracy and traceability to the transcript.
2. Correct identification of attendees, decisions, action items, deadlines, and unresolved questions.
3. Strict compliance with the output schema.
4. Correct, natural Bosnian in Latin script, with proper diacritics and punctuation.
5. Concise, nonredundant output.

Never sacrifice factual accuracy to produce a more complete-looking result. Missing or ambiguous information must remain explicitly unknown.

# 1. FUNDAMENTAL RULES

## 1.1. Evidence and uncertainty

Extract information only when it is explicitly stated or sufficiently supported by the transcript.

You may use contextual reasoning to interpret incomplete sentences, resolve obvious transcription errors, connect references to previously identified speakers, and reconstruct the intended meaning of an utterance.

However, contextual reasoning must never become unsupported factual invention.

Apply these rules:

- Use JSON `null` for unavailable or insufficiently supported scalar values where the schema permits it.
- Use an empty array `[]` when no entries of an array type can be established.
- Never use the string `"null"` to represent missing information.
- Never invent names, roles, dates, locations, decisions, task owners, or deadlines.
- Never add speculative language such as "vjerovatno", "moguće", or "najvjerovatnije" to compensate for uncertainty.
- Do not turn assumptions into facts merely because they seem plausible.
- Do not duplicate the same information across multiple entries unless the schema requires it.

When multiple interpretations are possible, evaluate the full transcript, including cross-references, direct forms of address, participant lists, repeated conversational patterns, and valid elimination across distinct speaker labels. Resolve ambiguity whenever this evidence establishes a unique, sufficiently supported interpretation. If the ambiguity cannot be resolved reliably, preserve the uncertainty using `null` or the appropriate uncertainty field. Do not leave an identity unknown merely because it is not explicitly attached to a numbered speaker label when the transcript establishes it through reliable cross-reference or elimination.

## 1.2. Source fidelity

The transcript is the primary source of truth.

Do not introduce external facts, background knowledge, customary procedures, assumed organizational structures, or information from unrelated meetings.

Do not treat a statement as confirmed merely because it sounds authoritative.

Preserve the intended meaning of statements, including their scope, conditions, negations, and degree of commitment.

Do not strengthen:
- Suggestions into decisions.
- Possibilities into commitments.
- Questions into statements of fact.
- Conditional agreements into unconditional agreements.
- Tentative deadlines into confirmed deadlines.

## 1.3. Distinguish speakers from people mentioned

A person mentioned in the transcript is not automatically a speaker, attendee, decision-maker, or task owner.

Maintain these distinctions throughout extraction:

- Speaker: a person who actually speaks in the transcript.
- Attendee: a person whose presence at the meeting is established by the available evidence.
- Absent person: a person explicitly identified as absent.
- Person mentioned: a person referred to during the discussion.
- Action owner: a person explicitly assigned or clearly committed to performing a task.

Do not infer attendance solely from being mentioned, being assigned a task, holding a position, or appearing on a list of people expected to attend.

# 2. LANGUAGE AND TEXT NORMALIZATION

All textual values in the output must be written in Bosnian, using Latin script.

The source transcript may be in Bosnian, English, or a mixture of both.

Apply the following rules:

- Translate English statements into natural Bosnian.
- Restore Bosnian diacritics, including č, ć, š, ž, and đ.
- Correct obvious spelling, punctuation, grammar, and transcription errors.
- Use standard Bosnian vocabulary and grammatical constructions.
- Do not output Cyrillic.
- Do not use Croatian wording or Croatian localization in reconstructed text. When interpreting a shared or ambiguous expression, prefer the standard Bosnian equivalent.
- Preserve names, official organization names, product names, and platform names in their established forms.
- Do not translate proper names.
- Do not change the substance of a statement while correcting its language.
- Do not silently resolve substantive ambiguities through grammatical rewriting.

All descriptions, decision texts, topics, questions, and explanatory notes must follow these language requirements.

Exception: `due_original` must preserve the exact original deadline wording from the transcript, including its original language. Do not translate, normalize, or correct that value.

# 3. SPEAKER IDENTIFICATION AND CROSS-REFERENCE RESOLUTION

When speaker labels or names are missing, incomplete, or represented only by numbered labels such as "Speaker 1", "Speaker 2", or "Govornik 1", actively reconstruct speaker identities using all reliable evidence available throughout the entire transcript.

**The objective is to identify the actual person behind each speaker label whenever the transcript provides sufficient direct, contextual, or relational evidence. Do not leave a speaker unidentified merely because their name is never explicitly attached to their numbered speaker label.**

## 3.1. Evidence sources

Use the following evidence, in descending order of reliability:

1. Explicit self-identification, including statements such as "Ja sam Amir", "Ovdje Lejla" or "Moje ime je Haris".
2. Explicit attribution by another participant, including statements that directly associate a name with a speaker.
3. Direct forms of address, including instances where one participant calls another participant by name, such as "Amire, možeš li objasniti?" or "Lejla, slažeš li se?"
4. An explicitly stated meeting roster, attendance list, participant introduction, or roll call that establishes the names of people participating in the meeting.
5. Repeated conversational patterns that reliably connect a numbered speaker label with a person identified elsewhere in the transcript.
6. Cross-reference and elimination reasoning based on the established identities of other speakers, provided that the remaining candidate is uniquely determined and the underlying assumptions are supported by the transcript.
7. Other contextual evidence that establishes identity without relying on speculative assumptions about occupation, seniority, expertise, opinions, writing style, or presumed organizational roles.

Use multiple independent pieces of evidence whenever possible. A single weak contextual clue must not override explicit contradictory evidence.

## 3.2. Global identity-resolution procedure

Do not identify speakers by analyzing each utterance in isolation. Build and continuously update a global speaker-identity map covering the entire transcript.

For each numbered or otherwise unidentified speaker:

1. Collect every utterance attributed to that speaker label.
2. Identify all names explicitly used by that speaker or by other participants when addressing or referring to that speaker.
3. Distinguish names used to address the speaker from names used to refer to third parties.
4. Identify the people explicitly listed as meeting participants, including any names provided during introductions, roll calls, or attendance checks.
5. Associate speaker labels with names when direct evidence supports the association.
6. Track which established identities have already been assigned to other distinct speaker labels.
7. Compare the remaining unidentified speaker labels against the remaining plausible participant identities.
8. Resolve an identity through elimination only when the candidate set, relevant speaker distinctions, and participant roster are sufficiently established to make the conclusion unique.
9. Revisit earlier identifications whenever new evidence appears later in the transcript.
10. Resolve all speaker identities before finalizing attendee names, action owners, decisions, or other fields that depend on speaker attribution.

Do not finalize an identity prematurely. Later utterances may establish a name that was initially unknown or reveal that an earlier attribution was incorrect.

## 3.3. Name inference through elimination

**When a transcript contains a complete or otherwise reliably established list of meeting participants, and all but one participant can be confidently matched to distinct numbered speaker labels, infer the remaining speaker's name for the final unmatched speaker label if the transcript supports a one-to-one correspondence.**

For example, suppose the transcript establishes that the meeting participants are Amir, Lejla, Haris, and Selma. The transcript contains four distinct numbered speakers. Direct forms of address and other reliable evidence establish that:

- Speaker 1 is Amir.
- Speaker 2 is Lejla.
- Speaker 3 is Haris.
- No direct identification of Speaker 4 has been found.

If the evidence establishes that all four listed people are the four distinct speakers, with no additional speakers or ambiguity about attendance, identify Speaker 4 as Selma.

Do not leave Speaker 4 unidentified simply because nobody explicitly says "I am Selma" or directly addresses Speaker 4 by that name.

Apply this reasoning to any number of participants and speakers, not just four.

However, elimination is valid only when its prerequisites are supported. Do not force a match when:

- The participant list may be incomplete.
- Some listed people may be attendees who never speak.
- The transcript may contain additional unlisted speakers.
- A single person may appear under multiple speaker labels.
- Multiple people share the same name.
- The number of established participants differs from the number of distinct speakers without a reliable explanation.
- An allegedly identified participant may actually be a person mentioned rather than a participant.
- Two or more candidate identities remain plausible.

In these cases, preserve the identity as unknown unless further evidence resolves the ambiguity.

## 3.4. Interpreting names used in conversation

Names used during conversation are valuable identity evidence, but their grammatical and conversational function must be interpreted correctly.

Distinguish between:

- **Direct address:** "Amire, pošalji nam izvještaj." The name identifies the person being addressed, not necessarily the speaker.
- **Self-reference:** "Ja sam Amir" or "Kao što sam ranije rekao, ja, Amir..." The name identifies the speaker when the context is unambiguous.
- **Third-party reference:** "Amir će poslati izvještaj." This identifies Amir as the person being discussed, not automatically as the current speaker or an attendee.
- **Reported speech:** "Lejla mi je rekla: 'Amire, dođi sutra.'" The name in the quoted statement does not automatically identify the current speaker.
- **Vocative or conversational shorthand:** A name may refer to the person being addressed, but only when the utterance's context supports that interpretation.
- **Ambiguous name usage:** If it is unclear whether a name identifies the speaker, the addressee, or a third party, do not treat the reference as conclusive evidence.

When a participant repeatedly addresses a numbered speaker by the same name, consistently use that evidence to establish the addressee's identity, provided the conversational structure makes the reference unambiguous.

## 3.5. Identity consistency and conflicting evidence

Maintain a consistent mapping between speaker labels and real identities throughout the transcript.

A confirmed identity must not be arbitrarily reassigned to another distinct speaker label.

If two labels appear to correspond to the same person, determine whether the transcript supports a repeated label, transcription error, label inconsistency, or two distinct individuals. Do not assume that either label represents a different person merely because its number differs.

If explicit evidence conflicts with an inferred identity, prioritize the strongest direct evidence and reassess the inference.

If the transcript establishes that a name belongs to a particular speaker, use that name consistently even when the person is not directly addressed by name in every utterance.

Never present an internally generated label, such as "Speaker 1", as a person's real name.

## 3.6. Confidence threshold and downstream use

Infer names when the evidence is sufficiently strong, including through valid elimination, rather than defaulting unnecessarily to an unknown identity.

At the same time, do not invent identities merely to complete the mapping.

A name may be used in an output field only when its association with the relevant person is supported by the transcript. If multiple interpretations remain plausible and the schema permits an unknown value, use `null`.

Apply the resolved identity map consistently to:

- `attendees`: include the established name of a person whose attendance is supported by the evidence.
- `absent`: include only people explicitly established to be absent.
- `action_items.owner`: use the resolved name when the task assignment or accepted commitment can be reliably attributed to that person.
- `decisions.lines` and `action_items.lines`: cite the original lines supporting the relevant facts, including identity evidence when needed.
- `open_questions`: preserve the substance of unresolved issues without introducing unsupported attribution.

A person's identity and attendance are separate questions. Successfully identifying a speaker does not, by itself, establish the identity of every other attendee or prove that every person on a roster was present.

Do not expose internal candidate lists, identity maps, elimination steps, confidence assessments, or reasoning in the final output. Return only the JSON required by the output schema.

# 4. MEETING METADATA

Extract the following fields:

- `title`: The meeting title, as explicitly provided or unambiguously established by the transcript. If unavailable, use `null`. Do not invent a formal title from the discussion.
- `date`: The meeting date in `YYYY-MM-DD` format. If the date cannot be established, use `null`.
- `location`: The physical meeting location or virtual meeting platform. If unavailable, use `null`.

Use an explicit meeting date or an unambiguous date reference in the transcript when available.

Do not assume that the date the transcript was created, uploaded, or processed is the meeting date.

Do not infer a virtual platform merely because the transcript contains remote participants.

If a date is given in an unambiguous format other than `YYYY-MM-DD`, normalize it to `YYYY-MM-DD`.

If the date is incomplete or ambiguous and cannot be resolved using reliable evidence within the transcript, use `null`.

# 5. ATTENDEES AND ABSENTEES

## 5.1. Attendees

`attendees` must be an array of objects containing exactly these keys:

- `name`
- `role`

Include only people whose attendance is established by the transcript or by an explicit, reliable attendance record included in the provided input.

A participant's name may be established through the speaker-identification and cross-reference procedure in Section 3, including valid elimination from a complete participant roster. Do not require the name to be explicitly spoken by that person or directly attached to their speaker label. However, identifying a person as a speaker does not justify including other people from a participant list unless their attendance is independently established.

Each attendee's `name` must be a string containing the person's established full name, or `null` if the person is established to be present but their name cannot be identified.

Each attendee's `role` must be a string describing an explicitly established role, or `null` if no special role is established.

Role rules:

- Do not assume a person's role from their speaking style, knowledge, seniority, or subject matter.
- Do not assign generic roles merely to fill the field.
- If the meeting is explicitly restricted to members of a committee, team, or similar body, and ordinary membership is established, use `null` for ordinary members whose only relevant role is membership.
- Include a special role, such as chairperson, president, secretary, or project lead, only when explicitly established by the evidence.
- Do not invent a person's role based on their participation in a discussion.
- Never use hedging expressions in the role field.

If the transcript explicitly establishes a person's attendance but not their role, set `role` to `null`.

Do not include a person in both `attendees` and `absent`.

## 5.2. Absentees

`absent` must be an array of strings containing the names of people explicitly established to be absent.

Include a person only when their absence is stated or reliably established by an explicit attendance record.

Do not classify someone as absent merely because they do not speak or are not mentioned throughout the transcript.

Do not include attendees in `absent`.

If an absent person's identity is not sufficiently established, do not invent a name or insert `null` into this array. Omit that person's entry.

# 6. TOPICS

`topics` must be an array of strings.

Include the substantive agenda items and subjects actually discussed.

Rules:

- Summarize topics concisely in Bosnian.
- Include distinct substantive topics even if they did not result in a decision.
- Merge repetitive references to the same topic.
- Do not include unrelated conversation, greetings, or administrative filler unless substantively relevant.
- Do not present a proposed action or a question as a confirmed decision.
- Do not invent an agenda that is not supported by the discussion.
- Do not include dates in topic descriptions.
- Avoid duplicate topics expressed with slightly different wording.

The topics array may be empty if no substantive topic can be established.

# 7. DECISIONS

`decisions` must be an array of objects containing exactly these keys:

- `text`
- `lines`

Include only final, confirmed decisions that were actually reached during the meeting.

A decision may be included when the transcript establishes that the participants agreed on, approved, rejected, selected, authorized, or otherwise definitively resolved a matter.

Do not include:

- Suggestions that were never accepted.
- Ideas that were merely discussed.
- Questions that remained unresolved.
- Conditional proposals that were not finalized.
- Preliminary agreements subsequently withdrawn or replaced.
- Statements of personal opinion.
- Actions that were discussed but not actually agreed upon as decisions.

When a decision changes during the meeting, record only the final confirmed version. Do not preserve superseded versions as separate decisions.

If the apparent final position remains ambiguous, do not represent it as a confirmed decision.

Write `text` as a concise, grammatically correct Bosnian statement.

Do not include dates in `text`.

The `lines` field must be an array of integers identifying the original transcript line numbers that directly support the decision.

Include all relevant lines needed to establish the final decision, including clarification or confirmation when necessary.

Do not invent line numbers. Use the actual line numbers provided in the input. If the transcript contains no line numbers, use `[]`.

Every decision object must contain both keys, even when `lines` is empty.

# 8. ACTION ITEMS

`action_items` must be an array of objects containing exactly these keys:

- `description`
- `owner`
- `due_date`
- `due_original`
- `confident`
- `note`
- `lines`

Each action item must represent a concrete task that someone is expected or explicitly committed to perform.

Include tasks that were explicitly assigned or unambiguously accepted as commitments.

Do not turn a general aspiration, hypothetical suggestion, unresolved proposal, or vague expression of intent into a definite action item.

## 8.1. Description

`description` must be a concise Bosnian description of the required task.

Use the infinitive form, as in:

- "Pripremiti izvještaj"
- "Poslati zapisnik učesnicima"
- "Provjeriti dostupnost prostorije"
- "Dostaviti potrebnu dokumentaciju"

Do not add ending punctuation.

Do not include deadlines in `description`.

Describe the task itself, not the discussion surrounding it.

## 8.2. Owner

`owner` must be the full name of the person explicitly assigned to perform the task or who clearly accepts responsibility for it.

Use `null` if the owner cannot be established.

Do not automatically assign a task to:
- The person who proposed it.
- The person who mentioned it.
- The meeting chairperson.
- The person responsible for a related task.
- The person whose role makes the assignment seem plausible.

If responsibility is explicitly assigned to multiple named people and cannot be represented accurately by a single owner, create separate entries only when the transcript establishes distinct individual responsibilities. Otherwise, use `null` rather than misrepresenting collective responsibility as an individual assignment.

Do not invent an individual owner for an action assigned only to an unnamed team or organization.

## 8.3. Due date

`due_date` must be a string in `YYYY-MM-DD` format if the deadline can be determined reliably. Otherwise, use `null`.

Resolve relative dates using the meeting date, not the current date.

Examples of relative expressions include:

- "sutra"
- "prekosutra"
- "danas"
- "večeras"
- "do petka"
- "sljedeće sedmice"
- "za dvije sedmice"
- "krajem mjeseca"

Interpret these expressions in the context of the original statement and the meeting date.

Rules:

1. Establish the meeting date before resolving relative deadlines.
2. Use explicit calendar dates whenever they are unambiguous.
3. Resolve relative expressions only when the reference date and intended time period are sufficiently clear.
4. Interpret the speaker's intended calendar period rather than mechanically choosing the nearest matching weekday.
5. Consider relevant contextual references to the month, week, year, or a previously mentioned event.
6. Do not use the current date as a substitute for an unknown meeting date.
7. Do not invent a year when the available evidence cannot establish it.
8. If the intended deadline cannot be resolved reliably, set `due_date` to `null`.

A date-only field cannot represent an exact time of day. If the transcript gives a specific hour, preserve the deadline wording in `due_original`; do not fabricate a time component in `due_date`.

## 8.4. Original deadline wording

`due_original` must preserve the exact deadline expression used in the transcript.

Examples:

- "do petka"
- "sutra"
- "do 15. novembra"
- "by Friday"
- "by the end of next week"

Do not translate or normalize this field.

If no deadline is stated or established, use `null`.

Do not substitute a calculated date for the original wording.

## 8.5. Deadline confidence and note

`confident` must be a JSON boolean.

Set `confident` to `true` when:
- A stated deadline is unambiguous, or
- A relative deadline can be resolved reliably to a calendar date using the meeting date and available context.

Set `confident` to `false` when:
- A deadline is stated but its intended calendar date or period remains ambiguous.
- The reference date needed to resolve a relative deadline is unavailable.
- Multiple plausible deadline interpretations remain.
- The wording does not establish a sufficiently precise deadline.

When `confident` is `false`, `note` must be a concise Bosnian string explaining the specific uncertainty.

When `confident` is `true`, `note` must be JSON `null`.

If no deadline was stated at all, set:
- `due_date` to `null`
- `due_original` to `null`
- `confident` to `false`
- `note` to a concise Bosnian explanation that no deadline was specified.

Do not invent a deadline to make an action item appear complete.

Do not include dates in `note`.

## 8.6. Action item evidence

`lines` must be an array of integers identifying the original transcript line numbers supporting the action item.

Include the lines establishing the task and, when available, the responsible person and deadline.

Use only actual source line numbers. If line numbers are not available in the input, use `[]`.

Do not invent line numbers or substitute timestamps for line numbers.

# 9. OPEN QUESTIONS

`open_questions` must be an array of objects containing exactly these keys:

- `text`
- `lines`

Include substantive questions that were raised during the meeting and remained unresolved when the meeting ended.

Examples include:
- A decision that was explicitly deferred.
- A question for which no answer was reached.
- An unresolved choice between alternatives.
- A request for information that remained unanswered.

Do not include questions that were subsequently answered or definitively resolved.

Do not classify a question as unresolved solely because the transcript does not record an answer if its resolution is otherwise explicitly established.

`text` must:
- Be written in Bosnian.
- Be formulated as a direct question.
- End with a question mark.
- Express the actual unresolved issue without adding assumptions.

Do not include dates in `text`.

`lines` must be an array of integers identifying the transcript lines that support the existence and unresolved status of the question.

Use actual source line numbers only. If line numbers are not available, use `[]`.

Do not add explanatory notes, parenthetical comments, recommendations, proposed next steps, or statements about discussing the question at a future meeting.

Each object must contain exactly `text` and `lines`.

# 10. LINE NUMBER INTEGRITY

Line numbers are evidence references to the transcript's original text, not generated annotations that must already exist.

Determine line numbers from the transcript exactly as it appears in the input message, even when the transcript is embedded directly in the message rather than provided as a file.

If the transcript does not contain explicit line numbers, infer them by counting physical lines of text, starting with line 1 at the first line of the transcript itself. Do not count system instructions, user instructions, surrounding explanations, or other text outside the transcript.

Count each newline-separated line as one line, including blank lines if they occur within the transcript. Do not count the surrounding Markdown code fences or other formatting delimiters as transcript lines.

If the input provides explicit, reliable source line numbers, preserve those original numbers in the `lines` arrays rather than recalculating them.

When explicit line numbers are absent, use the inferred line numbers. Do not return an empty `lines` array merely because the transcript was not pre-numbered or provided as a file.

Use only line numbers that correspond to actual lines in the provided transcript and directly support the associated decision, action item, or open question. Include multiple line numbers when the evidence spans several utterances.

Never invent line numbers, use numbers outside the transcript's actual line range, or cite lines that do not support the associated entry. If the transcript is genuinely absent, empty, or impossible to map reliably to lines, return an empty array for `lines`.

# 11. STRICT JSON SCHEMA

Return one valid JSON object containing exactly the following top-level keys:

- `title`
- `date`
- `location`
- `attendees`
- `absent`
- `topics`
- `decisions`
- `action_items`
- `open_questions`

The required structure is:

{
  "title": null,
  "date": null,
  "location": null,
  "attendees": [],
  "absent": [],
  "topics": [],
  "decisions": [],
  "action_items": [],
  "open_questions": []
}

This is a structural example, not a template to copy blindly. Populate each field using the transcript.

## Required data types

- `title`: string or null.
- `date`: string in `YYYY-MM-DD` format or null.
- `location`: string or null.
- `attendees`: array of objects with exactly `name` and `role`.
- `attendees[].name`: string or null.
- `attendees[].role`: string or null.
- `absent`: array of strings.
- `topics`: array of strings.
- `decisions`: array of objects with exactly `text` and `lines`.
- `decisions[].text`: string.
- `decisions[].lines`: array of integers.
- `action_items`: array of objects with exactly `description`, `owner`, `due_date`, `due_original`, `confident`, `note`, and `lines`.
- `action_items[].description`: string.
- `action_items[].owner`: string or null.
- `action_items[].due_date`: string in `YYYY-MM-DD` format or null.
- `action_items[].due_original`: string or null.
- `action_items[].confident`: boolean.
- `action_items[].note`: string or null.
- `action_items[].lines`: array of integers.
- `open_questions`: array of objects with exactly `text` and `lines`.
- `open_questions[].text`: string.
- `open_questions[].lines`: array of integers.

Do not add any other fields.

Do not omit required fields from any object.

Do not use strings for booleans, numbers, or null values.

Use `[]` when an array has no supported entries.

Use `null` only for missing or indeterminate scalar values where explicitly permitted.

Do not use trailing commas, comments, Markdown code fences, or any syntax that makes the output invalid JSON.

# 12. FINAL VALIDATION

Before producing the final answer, silently perform the following checks.

## Factual validation

- Every extracted fact is supported by the transcript.
- Attendees are not confused with people merely mentioned.
- Absentees are explicitly established as absent.
- Speaker identities are not guessed.
- Roles are supported by evidence.
- Decisions are final and confirmed.
- Superseded decisions are excluded.
- Action items represent concrete, supported commitments.
- Action owners are not invented.
- Relative deadlines are calculated from the meeting date.
- Ambiguous or unavailable dates are handled according to the schema.
- Open questions remain genuinely unresolved.

## Language validation

- All textual values are in natural Bosnian using Latin script, except `due_original`, which preserves the source wording.
- Bosnian diacritics and punctuation are correct.
- Grammar and spelling have been corrected without changing meaning.
- Descriptions are in infinitive form and have no ending punctuation.
- Open questions are interrogative and end with question marks.
- No dates appear in `text`, `description`, or `note` fields.

## Structural validation

- The output is exactly one JSON object.
- All nine required top-level keys are present.
- No additional keys are present.
- Every field has the required data type.
- Unknown scalar values use JSON `null`, never the string `"null"`.
- Every `lines` field is an array of integers.
- All dates follow `YYYY-MM-DD`.
- All action items contain all seven required fields.
- All decisions and open questions contain both required fields.
- The JSON is syntactically valid and can be parsed by a standard JSON parser.

If any check fails, correct the output before returning it.

# 13. OUTPUT RESTRICTIONS

Return only the final JSON object.

Do not include explanations, summaries, introductory text, Markdown code fences, comments, warnings, or follow-up messages.

Do not reveal your reasoning or validation process.

Accuracy takes priority over completeness. When the transcript does not support a reliable conclusion, preserve the uncertainty rather than inventing information.

# INPUT TRANSCRIPT

"""

def take_minutes(transcript, /):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={
            "model": os.getenv("OPENROUTER_MODEL_ID"),
            "messages": [
                {
                    "role": "user",
                    "content": f"{INSTRUCTIONS}```\n{transcript}```\n"
                }
            ]
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv("OPENROUTER_API_KEY")}"
        }
    )
    if not response.ok:
        raise Exception(response.text)
    return json.loads(response.json()["choices"][0]["message"]["content"])

def write_md(file, data, /):
    def cvt_date(date, /):
        return datetime.datetime.strftime(
            datetime.datetime.strptime(date, "%Y-%m-%d"), "%d. %m. %Y."
        )
    def make_lines_text(lines, /):
        return (
            ""
            if not lines else
            f"{lines[0]}"
            if len(lines) == 1 else
            f"{lines[0]}-{lines[-1]}"
        )
    file.write(
        f"# {data["title"]} (" +
        f"{"" if data["location"] is None else f"{data["location"]}, "}" +
        f"{cvt_date(data["date"])})\n\n### Prisutni\n\n"
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
    file.write(f"### Odluke\n\n|  | Odluka | Linije |\n|-|-|-|\n")
    for i in range(len(data["decisions"])):
        decision = data["decisions"][i]
        file.write(
            f"| {i + 1}. | {decision["text"]} | {make_lines_text(decision["lines"])} |\n"
        )
    file.write(
        f"\n### Zaduženja\n\n|  | Opis | Osoba | Krajnji rok | Dodatna napomena | Linije |" +
        "\n|-|-|-|-|-|-|\n"
    )
    for i in range(len(data["action_items"])):
        action_item = data["action_items"][i]
        file.write(
            f"| {i + 1}. | {action_item["description"]} " +
            f"| {"" if action_item["owner"] is None else action_item["owner"]} | {
                "?"
                if action_item["due_date"] is None else
                f"{cvt_date(action_item["due_date"])} (\"{action_item["due_original"]}\")"
            }" +
            f"| {("" if action_item["confident"] else action_item["note"])} " +
            f"| {make_lines_text(action_item["lines"])} |\n"
        )
    file.write("\n### Otvorena pitanja\n\n|  | Pitanje | Linije |\n|-|-|-|\n")
    for i in range(len(data["open_questions"])):
        open_question = data["open_questions"][i]
        file.write(
            f"| {i + 1}. | {open_question["text"]} " +
            f"| {make_lines_text(open_question["lines"])} |\n"
        )

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
