"""Mock AI responses (creative briefs, storyboards, reviews) for the test scenarios."""

from copy import deepcopy

CAMERAS = ["eye level, static, 24mm wide lens", "slow push-in, eye level, 35mm", "tight framing, 85mm, shallow depth",
           "macro lens, locked off", "low angle, slight upward tilt", "high wide angle, slow pan",
           "side profile, tracking left", "wide, handheld energy", "low angle, slow crane up"]
SHOTS = ["Extreme wide shot", "Medium shot", "Close-up portrait", "Detail shot", "Low-angle or dramatic medium shot",
         "Wide shot", "Side profile or cinematic angle", "Wide action shot", "Low-angle hero shot"]


def brief(story_type="motivational", lang="en", kind="human", subject="a tired young woman", **kw):
    b = {
        "input_language": lang,
        "core_message": "Even during difficult times, there is always hope.",
        "storytelling_objective": "Make viewers feel that darkness is temporary.",
        "target_audience": "",
        "story_type": story_type,
        "story_type_reason": "The message is about overcoming hardship.",
        "genre": "Inspirational drama",
        "emotional_tone": "Heavy and grey, slowly turning warm and hopeful",
        "narrative_theme": "Resilience",
        "main_subject": {"kind": kind, "description": subject},
        "visual_environment": "A coastal village during a storm",
        "beginning": "She walks alone through the storm.",
        "progression": "She keeps going despite setbacks.",
        "ending": "Sunrise breaks over the sea as she smiles.",
        "viewer_takeaway": "Keep going; light returns.",
        "explicit_requirements": [],
        "creative_decisions": ["Chose a coastal storm as the visual metaphor for hardship."],
        "factual_cautions": [],
    }
    b.update(kw)
    return b


def _beats(spec, lighting=None, weights=None):
    beats = []
    for i, (title, visual, action) in enumerate(spec):
        beats.append({
            "panel": i + 1, "title": title, "purpose": f"Story stage {i + 1}: {title.lower()}",
            "shot_type": SHOTS[i], "camera": CAMERAS[i],
            "visual_description": visual, "action": action,
            "lighting": (lighting[i] if lighting else "Soft consistent key light from the left, gentle haze"),
            "continuity_notes": "Same subject, same location and style as the previous panel",
            "relative_weight": (weights[i] if weights else [1, 1, 1, 1, 1, 1, 1, 1.3, 1.7][i]),
        })
    return beats


def storyboard(story_type="motivational", title="AFTER THE STORM", character=None, product=None,
               environment=None, fixed=None, changes=None, spec=None, lighting=None, style=None, avoid=None,
               weights=None):
    spec = spec or HOPE_SPEC
    return {
        "title": title,
        "core_message": "Even during difficult times, there is always hope.",
        "story_type": story_type,
        "narrative_structure": ["Challenge", "Struggle", "Decision", "Progress", "Transformation", "Resolution"],
        "emotional_goal": "From heaviness to quiet hope",
        "viewer_takeaway": "Keep going; light returns.",
        "concept": ("A young fisherwoman walks alone through a violent coastal storm toward the harbor. She "
                    "struggles, falls, gets up and keeps going. As she reaches the pier the clouds break and a "
                    "warm sunrise spreads over the sea."),
        "visual_style": style or "Photorealistic cinematic film still, anamorphic 2.39:1, fine film grain",
        "color_palette": "Desaturated storm blues and greys shifting to warm amber and gold",
        "character": character if character is not None else {
            "present": True, "name": "Mara", "description": "Young fisherwoman, late 20s, short dark wet hair, "
                                                            "freckles, determined brown eyes",
            "outfit": "Yellow oilskin raincoat, dark wool sweater, black rubber boots",
            "accessories": "Small brass compass on a cord", "supporting_characters": []},
        "product": product if product is not None else {"present": False, "name": "", "description": ""},
        "environment": environment or {
            "location": "Rocky fishing village harbor", "description": "Stone pier, moored wooden boats, "
                                                                       "white cottages on a hill",
            "time_of_day": "Pre-dawn, violent rainstorm", "key_objects": ["stone pier", "red lighthouse"]},
        "continuity": {
            "fixed_attributes": fixed or ["Mara's face and short dark hair", "Yellow oilskin raincoat",
                                          "Stone pier and red lighthouse", "Anamorphic photoreal film look"],
            "intentional_changes": changes if changes is not None else [],
        },
        "beats": _beats(spec, lighting, weights),
        "avoid": avoid if avoid is not None else ["text overlays"],
    }


HOPE_SPEC = [
    ("STORM HARBOR", "Tiny figure in a yellow raincoat on a long stone pier, huge waves crash, red lighthouse far away",
     "Mara walks into the storm toward the lighthouse."),
    ("AGAINST THE WIND", "Mara leans into horizontal rain, raincoat whipping, boats rocking behind her",
     "She pushes forward against the wind."),
    ("WET FACE", "Rain streams down Mara's freckled face, eyes squinting but determined",
     "Her eyes lock on the distant light."),
    ("THE COMPASS", "Brass compass in her wet gloved hand, needle trembling, raindrops on glass",
     "She grips the compass tightly."),
    ("SHE FALLS", "Mara on one knee on slick stones, a wave spraying over the pier edge",
     "A wave knocks her to her knees."),
    ("GETTING UP", "Mara pushing herself up with one hand, the lighthouse beam sweeping above",
     "She rises and keeps walking."),
    ("CLOUDS BREAK", "Side view of Mara at the pier end, first gap opening in the dark clouds",
     "A thin line of gold cuts the clouds."),
    ("SUNRISE", "Wide sea under a warm sunrise, calm water, Mara small at the pier end",
     "Sunlight floods across the sea."),
    ("HOPE", "Mara in warm golden light, soft smile, wet raincoat glowing, lighthouse behind",
     "She smiles into the rising sun."),
]
HOPE_LIGHTING = (["Cold blue storm light, heavy rain"] * 4 + ["Dark storm, lighthouse beam"] * 2 +
                 ["First warm gold through the clouds", "Warm golden sunrise", "Warm golden backlight"])
HOPE_CHANGES = [{"attribute": "lighting", "change": "cold blue storm light -> warm golden sunrise",
                 "panels": "panels 1-6 -> 7-9"},
                {"attribute": "expression", "change": "strain -> soft smile", "panels": "panels 3 -> 9"}]

FANTASY_SPEC = [
    ("FROZEN PEAKS", "Endless snowy mountain range under a pale green aurora, a lone knight on a ridge",
     "The knight stands alone on the ridge."),
    ("SNOW STIRS", "Medium shot of the knight, snow lifting off the ridge in spirals around her fur cloak",
     "The wind begins to howl."),
    ("SHE LISTENS", "Close-up of the knight's scarred face under a silver helm, breath visible",
     "Her eyes narrow toward the peaks."),
    ("RUNES GLOW", "Detail of her sword hilt, blue runes starting to glow through the frost",
     "The runes on her sword ignite."),
    ("MOUNTAIN SHAKES", "Low angle on the knight, avalanches sliding down the peaks behind her",
     "The mountain trembles beneath her."),
    ("WINGS IN THE AURORA", "Huge winged silhouette crossing the aurora above distant peaks",
     "A vast shadow glides through the sky."),
    ("SHE TURNS", "Side profile of the knight drawing her glowing sword, snow swirling",
     "She turns and draws her sword."),
    ("THE ICE DRAGON", "Colossal ice dragon landing on the ridge, crystalline wings spread, snow exploding",
     "The ice dragon lands before her."),
    ("FACE TO FACE", "Low-angle hero shot of the knight raising her glowing sword toward the dragon",
     "She raises her blade, unafraid."),
]

AD_SPEC = [
    ("DRY AFTERNOON", "Runner on a hot city track, sweat dripping, empty plastic bottle crushed in hand",
     "A runner stops, out of breath."),
    ("RUNNING ON EMPTY", "Runner bent over, hands on knees, heat haze rising from the track",
     "Her pace collapses in the heat."),
    ("THE THIRST", "Close-up of the runner's dry lips and tired eyes", "She closes her eyes, exhausted."),
    ("AQUAPURE APPEARS", "Detail of the AquaPure bottle: matte teal steel bottle with white wave logo, "
                         "condensation beads on its side",
     "The AquaPure bottle sits cold in her bag."),
    ("FIRST SIP", "Medium shot, runner drinking from the teal AquaPure bottle, light catching water droplets",
     "She takes a long, cold sip."),
    ("ENERGY RETURNS", "Wide shot of the runner sprinting again along the track, bottle clipped to her belt",
     "She surges back into her stride."),
    ("STAYS COLD", "Side angle of the bottle on a sunny bench, ice cubes visible through the open lid",
     "Ice still clinks inside after hours."),
    ("FINISH LINE", "Runner crossing a chalk finish line at sunset, arms raised, bottle in hand",
     "She crosses the line, beaming."),
    ("STAY COLD. KEEP GOING.", "Hero packshot of the teal AquaPure bottle on the track at golden hour",
     "AquaPure — stay cold, keep going."),
]

EDU_SPEC = [
    ("WHY GREEN?", "A curious girl in a sunlit garden holding a single green leaf up to the sky",
     "She wonders why leaves are green."),
    ("SUNLIGHT ARRIVES", "Sunbeams falling through the garden canopy onto rows of plants",
     "Sunlight pours onto the leaves."),
    ("INSIDE THE LEAF", "Stylized cross-section of a leaf showing tiny green chloroplasts",
     "We zoom inside the leaf."),
    ("CAPTURING LIGHT", "Glowing chloroplasts absorbing golden light particles", "Chloroplasts soak up the light."),
    ("WATER RISES", "Water droplets travelling up a transparent stem from the roots",
     "Water climbs up from the roots."),
    ("AIR GOES IN", "Tiny pores on the leaf surface pulling in faint blue CO2 particles",
     "The leaf breathes in carbon dioxide."),
    ("SUGAR IS MADE", "Glowing sugar crystals forming inside the leaf, bubbles of oxygen escaping",
     "Light turns into food and oxygen."),
    ("SHE UNDERSTANDS", "The girl smiling as she watches oxygen bubbles rise from pond plants",
     "Her face lights up with understanding."),
    ("PLANTS FEED THE WORLD", "Wide garden view, the girl watering a seedling in golden light",
     "Plants turn sunlight into life."),
]

SEED_SPEC = [
    ("CRACKED EARTH", "Dry cracked desert ground under a pale sky, one small seed lying in a crack",
     "A seed lies in the dry earth."),
    ("FIRST DROP", "A single raindrop hitting the cracked soil next to the seed, dust splashing",
     "The first raindrop falls."),
    ("RAIN ARRIVES", "Rain darkening the soil, water filling the cracks", "Rain soaks the parched ground."),
    ("THE SEED SPLITS", "Macro shot of the seed coat splitting, a pale root emerging", "The seed cracks open."),
    ("REACHING UP", "Tiny green sprout pushing through wet soil, droplets on its leaves",
     "A sprout pushes toward the light."),
    ("STORM PASSES", "Low wide view of the sprout as dark clouds roll away", "The storm clouds drift away."),
    ("LEAVES OPEN", "Side view of the young plant unfolding two leaves in soft light", "Its first leaves unfold."),
    ("BLOOM", "Wide shot of a single red desert flower blooming on the wet ground", "A red flower blooms."),
    ("LIFE RETURNS", "Low-angle shot of the flower against a clear blue sky, bees arriving",
     "Life returns to the desert."),
]


def review(alignment=5):
    r = {k: {"rating": alignment, "comment": "Clear and on message."} for k in
         ("message_alignment", "story_progression", "visual_clarity", "scene_consistency", "ending_strength",
          "repetition")}
    r.update(contradictions=[], suggestions=["Consider a tighter close-up in panel 3."],
             summary="Coherent, message-aligned storyboard.")
    return r


def new_beat(panel=4, title="HANDS ON THE COMPASS", visual="Extreme close-up of Mara's trembling hands "
                                                              "opening the brass compass, rain on the glass"):
    return {"panel": panel, "title": title, "purpose": "Small detail shows resolve",
            "shot_type": "Extreme close-up", "camera": "macro, locked off, shallow depth",
            "visual_description": visual, "action": "She opens the compass and steadies her breath.",
            "lighting": "Cold blue storm light", "continuity_notes": "Same raincoat and compass",
            "relative_weight": 2.5}


def copy(x):
    return deepcopy(x)
