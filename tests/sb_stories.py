"""Regression stories for the prompt engine (test data only — never used by the application)."""

from sb_fixtures import NEUTRAL_SHOTS, storyboard

NO_CHARACTER = {"present": False, "name": "", "description": "", "outfit": "", "accessories": "",
                "supporting_characters": []}

# ---------------------------------------------------------------- Beyond the Matrix — Episode 1
MATRIX_MESSAGE = ("Beyond the Matrix — Episode 1: The Invisible Chains. A man realizes that habits, notifications "
                  "and expectations are invisible chains holding everyone around him.")
MATRIX_SPEC = [
    ("GREY MORNING", "A crowded open-plan office under cold fluorescent light, rows of identical desks, "
                     "Adam at his desk staring at three glowing monitors", "Adam types without looking up."),
    ("NOTIFICATIONS", "Close on Adam's phone buzzing on the desk, a stack of red notification badges, his hand "
                      "reaching automatically", "His hand reaches for the phone again."),
    ("FIRST GLIMPSE", "Close-up of Adam's face reflected in the dark monitor; faint translucent chains glint "
                      "around his wrists in the reflection only", "He notices thin chains in his reflection."),
    ("THE COMMUTE", "Packed subway car, commuters staring at phones, faint glowing chains linking each person "
                    "to their screen, Adam standing among them", "Adam sees chains on every commuter."),
    ("TESTING THE CHAIN", "Detail of Adam's hand gripping a faintly glowing chain at his wrist, links made of "
                          "tiny calendar icons and message bubbles", "He pulls at one chain."),
    ("RESISTANCE", "Adam on the subway platform as the crowd flows past him, the chain pulling his arm toward "
                   "the exit stairs", "The chain tugs him back into the flow."),
    ("ONE LINK BREAKS", "Adam alone on an empty rooftop at dawn, one chain link cracking apart in his hand, "
                        "city skyline behind", "A single link snaps open."),
    ("STILL BOUND", "Wide rooftop shot, Adam standing at the edge, the other chains still faintly visible, "
                    "trailing back toward the city", "He looks at the chains that remain."),
    ("THE QUESTION", "Adam's face in pale dawn light, half lit, gazing at the horizon, expression unreadable",
     "He wonders whether he is free or only aware."),
]
MATRIX_CHANGES = [
    {"attribute": "chains visibility", "change": "invisible -> faint reflection -> visible glowing chains",
     "panels": "panels 1-3 -> 4-9"},
    {"attribute": "environment", "change": "office -> subway -> rooftop at dawn", "panels": "panels 1-3 -> 4-6 -> 7-9"},
    {"attribute": "lighting", "change": "cold fluorescent white -> pale dawn gold", "panels": "panels 1-6 -> 7-9"},
]


def matrix_storyboard():
    sb = storyboard(
        "general", "BEYOND THE MATRIX — EPISODE 1: THE INVISIBLE CHAINS", spec=MATRIX_SPEC,
        character={"present": True, "name": "Adam", "description": "Office worker in his 30s from the reference "
                                                                   "image", "outfit": "Grey suit, loosened tie",
                   "accessories": "Smartphone", "supporting_characters": ["subway commuters", "office coworkers"]},
        environment={"location": "Modern city", "description": "Open-plan office, crowded subway, rooftop",
                     "time_of_day": "Grey weekday morning", "key_objects": ["smartphone", "glowing chains"]},
        fixed=["Adam's face and grey suit", "Chains are thin, translucent and faintly glowing",
               "Desaturated cinematic realism"],
        changes=MATRIX_CHANGES, style="Photorealistic cinematic film still, desaturated teal grade",
        lighting=["Cold fluorescent office light"] * 3 + ["Flat cold subway light"] * 3 + ["Pale dawn gold"] * 3,
        avoid=["neon cyberpunk clichés"])
    sb["core_message"] = "The chains that hold us are invisible habits we accept without noticing."
    sb["viewer_takeaway"] = "Awareness is the first step; freedom remains an open question."
    sb["emotional_goal"] = "From numb routine to unsettling awareness, ending on an open question"
    sb["concept"] = ("An office worker slowly notices invisible chains of habit and notification that bind him and "
                     "everyone around him. He breaks a single link at dawn, but the story ends on an open question: "
                     "is he free, or only aware?")
    return sb


# ---------------------------------------------------------------- Test D: environment transformation
DESERT_SPEC = [
    ("DRY HORIZON", "Endless cracked desert under a white-hot sky, bleached dunes to the horizon",
     "Heat shimmers over the empty desert."),
    ("FIRST CLOUD", "A single dark rain cloud forming over the dunes", "A cloud gathers above the sand."),
    ("RAIN", "Heavy rain falling on cracked earth, dark wet patches spreading", "Rain soaks the cracked ground."),
    ("SPROUTS", "Macro view of green sprouts pushing through wet sand", "Tiny sprouts break the surface."),
    ("STREAM", "A new stream winding between dunes, grass along its banks", "Water carves a path through the sand."),
    ("SPREADING GREEN", "Wide shot of grass and shrubs covering half the dunes", "Green spreads across the dunes."),
    ("TREES RISE", "Young palm and acacia trees growing beside the stream", "Trees rise along the water."),
    ("BLOOM", "Flowers blooming across a lush valley, birds arriving", "The valley bursts into bloom."),
    ("PARADISE", "Lush green paradise with waterfalls and trees where the desert once was, warm sunset light",
     "A green paradise stands where the desert was."),
]


def desert_storyboard():
    sb = storyboard("general", "THE GREENING", spec=DESERT_SPEC, shots=NEUTRAL_SHOTS, character=dict(NO_CHARACTER),
                    environment={"location": "Desert valley", "description": "Wide desert valley with dunes",
                                 "time_of_day": "Midday, harsh sun", "key_objects": ["dunes", "stream"]},
                    fixed=["Same valley and horizon line", "Photoreal nature-documentary look",
                           "Desert landscape of dunes"],
                    changes=[{"attribute": "landscape", "change": "barren desert -> lush green paradise",
                              "panels": "panels 1-3 -> 7-9"},
                             {"attribute": "lighting", "change": "harsh white midday -> warm golden sunset",
                              "panels": "panels 1 -> 9"}],
                    style="Photorealistic nature documentary, aerial and macro cinematography", avoid=[])
    sb["core_message"] = "Even the driest place can be transformed."
    sb["concept"] = ("A barren desert valley receives its first rain. Sprouts, a stream, grass, trees and flowers "
                     "spread until the whole valley becomes a lush green paradise.")
    return sb


# ---------------------------------------------------------------- Test A: motivational
FEAR_SPEC = [
    ("THE HIGH BOARD", "A swimming hall, a woman in a navy swimsuit standing at the bottom of a 10 m diving tower",
     "Lena looks up at the high board."),
    ("SHAKING HANDS", "Close on Lena's trembling hands gripping the cold ladder rail", "Her hands tremble on the rail."),
    ("CLIMB", "Low angle up the ladder as Lena climbs, water reflections on tiles", "She climbs one rung at a time."),
    ("THE EDGE", "Lena at the edge of the board, pool far below, toes over the edge", "She freezes at the edge."),
    ("STEP BACK", "Lena stepping back from the edge, eyes closed, breathing deeply", "She steps back and breathes."),
    ("COACH NODS", "Her coach on the pool deck giving a calm nod and thumbs up", "Her coach nods calmly."),
    ("DECISION", "Close-up of Lena opening her eyes, jaw set", "She opens her eyes, decided."),
    ("THE JUMP", "Lena mid-air in a clean pencil jump, arms tight", "She jumps."),
    ("SURFACING", "Lena surfacing, laughing, water splashing in bright hall light", "She surfaces, laughing."),
]


def fear_storyboard(contaminated=False):
    sb = storyboard("motivational", "THE HIGH BOARD", spec=FEAR_SPEC, shots=NEUTRAL_SHOTS,
                    character={"present": True, "name": "Lena", "description": "Woman in her 20s, short blonde hair",
                               "outfit": "Navy swimsuit", "accessories": "", "supporting_characters": ["her coach"]},
                    environment={"location": "Indoor swimming hall", "description": "Olympic pool with a 10 m "
                                 "diving tower", "time_of_day": "Afternoon", "key_objects": ["diving tower"]},
                    fixed=["Lena's face and navy swimsuit", "Swimming hall and diving tower",
                           "Bright natural photoreal look"], style="Photorealistic sports film still", avoid=[])
    sb["core_message"] = "Courage is acting while still afraid."
    sb["concept"] = ("A young woman afraid of heights climbs a 10 m diving tower, freezes, steps back, then decides "
                     "to jump and surfaces laughing.")
    if contaminated:
        sb["beats"][5]["visual_description"] = "A mysterious shadowy creature rises from the dark pool depths"
        sb["beats"][5]["title"] = "HIDDEN FORCE"
    return sb


# ---------------------------------------------------------------- Test B: product advertisement
PHONE_SPEC = [
    ("MISSED CALLS", "A busy small bakery, the owner Samir kneading dough while his wall phone rings unanswered",
     "Samir cannot reach the ringing phone."),
    ("LOST ORDERS", "Close on a counter tablet screen showing 4 missed calls in red", "Missed calls pile up."),
    ("SETUP", "Samir at the counter tapping the VoiceDesk app on a smartphone, simple setup screen visible",
     "He turns on the VoiceDesk assistant."),
    ("THE ASSISTANT ANSWERS", "Smartphone on the counter, the VoiceDesk screen showing a calm blue voice waveform "
                              "while a call comes in", "VoiceDesk answers the call."),
    ("ORDER TAKEN", "Tablet screen showing a neat order card reading '2 sourdough, pickup 5 pm'",
     "The order appears automatically."),
    ("BACK TO BAKING", "Samir calmly shaping loaves, phone quiet on the shelf", "Samir keeps baking, undisturbed."),
    ("CUSTOMER PICKUP", "A smiling customer picking up a paper bag of bread at the counter",
     "A customer collects her order."),
    ("FULL SHELVES", "Wide shot of the bakery with full shelves and a short queue of happy customers",
     "The bakery runs smoothly."),
    ("VOICEDESK", "Smartphone on the bakery counter showing the VoiceDesk logo, warm bread behind it",
     "VoiceDesk: never miss a customer."),
]


def phone_storyboard():
    sb = storyboard("advertising", "NEVER MISS A CUSTOMER", spec=PHONE_SPEC, shots=NEUTRAL_SHOTS,
                    character={"present": True, "name": "Samir", "description": "Bakery owner in his 40s",
                               "outfit": "White apron", "accessories": "", "supporting_characters": []},
                    product={"present": True, "name": "VoiceDesk", "description": "AI phone-assistant app with a "
                             "blue waveform icon and logo"},
                    environment={"location": "Small neighborhood bakery", "description": "Warm wooden bakery",
                                 "time_of_day": "Morning", "key_objects": ["smartphone", "tablet"]},
                    fixed=["Samir and his white apron", "VoiceDesk blue waveform UI", "Warm bakery interior"],
                    style="Clean commercial photoreal look, warm tones", avoid=[])
    sb["core_message"] = "An AI telephone assistant lets a small business answer every call."
    sb["concept"] = ("A busy baker keeps missing phone orders. He switches on the VoiceDesk AI assistant, which "
                     "answers calls and records orders so he can keep baking and serve every customer.")
    return sb


# ---------------------------------------------------------------- Test C: educational
PLANTS_SPEC = [
    ("A SEED", "Cross-section of soil with a single bean seed", "A seed rests in the soil."),
    ("WATER", "Water droplets soaking into the soil around the seed", "Water reaches the seed."),
    ("ROOT", "The seed splitting, a white root growing downward", "A root grows down."),
    ("SHOOT", "A pale shoot curving upward through the soil", "A shoot pushes upward."),
    ("FIRST LEAVES", "Two green leaves opening above the soil in sunlight", "The first leaves open."),
    ("SUNLIGHT", "Soft arrows of sunlight entering the leaves in a simple diagram style", "Leaves capture sunlight."),
    ("GROWING TALLER", "The stem lengthening in three overlapping growth stages", "The stem grows taller."),
    ("FLOWER", "A small white flower opening on the mature plant", "The plant flowers."),
    ("NEW SEEDS", "Green bean pods hanging from the plant, a pod opening to show seeds", "New seeds form."),
]


def plants_storyboard():
    sb = storyboard("educational", "HOW A PLANT GROWS", spec=PLANTS_SPEC, shots=NEUTRAL_SHOTS, character=dict(NO_CHARACTER),
                    environment={"location": "Garden soil", "description": "Cutaway soil view with sky above",
                                 "time_of_day": "Morning", "key_objects": ["bean seed"]},
                    fixed=["Same bean plant", "Same cutaway soil frame", "Clean educational 3D style"],
                    style="Clean educational 3D illustration, soft rounded shapes", avoid=[])
    sb["core_message"] = "Plants grow from seeds using water and sunlight."
    sb["concept"] = "A bean seed absorbs water, roots, sprouts, grows with sunlight, flowers and makes new seeds."
    return sb
