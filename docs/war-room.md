# War Room Prompt Builder | مولّد برومت «قاعة العمليات»

**File:** `war_room_prompt_builder.py` · **Needs:** Python 3.10+ (3.13 recommended) + tkinter, no key

Generates a ready-to-paste **“War Room” prompt** for any AI chatbot (Claude, ChatGPT, Gemini, …).
Instead of answering right away, the chatbot first transcribes a live debate between five roles:

| Role | Job |
|---|---|
| The Engineer (المهندس) | Builds the first solution |
| Devil’s Advocate (محامي الشيطان) | Attacks assumptions and finds fatal flaws |
| The “Dumb” Customer (الزبون الغبي) | A cynical end user who hates complexity |
| The Specialist (الخبير المتخصص) | The best-matched world expert, chosen for your problem |
| The Maestro (المايسترو) | Stays silent and observes until the final stage |

The rules forbid flattery and premature conclusions. Each critic must reject the first draft and name
at least one fatal flaw, so the final answer comes out much stronger.

## Install & run

```bash
python war_room_prompt_builder.py
# Windows with several Pythons installed:  py -3.13 war_room_prompt_builder.py
```

## How to use

1. Choose the prompt language: **العربية** or **English**.
2. Type your goal or problem (for example, *“Design a pricing strategy for my new app”*).
3. Generate the prompt, then copy it (or save it to a file).
4. Paste it into your chatbot. Let the debate run, then ask the Maestro for the final decision.
