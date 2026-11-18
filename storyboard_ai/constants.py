"""Shared lesson constants (re-exported by storyboard_prompt_generator for backward compatibility)."""

# Default 15 s timing from the lesson: beats 1-7 = 1.5 s, reveal = 2 s, hero = 2.5 s
BEAT_WEIGHTS = [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 2.0, 2.5]

SHOT_TYPES = [
    "Extreme wide shot",
    "Wide shot",
    "Medium shot",
    "Close-up portrait",
    "Extreme close-up",
    "Detail shot",
    "Low-angle or dramatic medium shot",
    "Low-angle hero shot",
    "Side profile or cinematic angle",
    "Over-the-shoulder shot",
    "High-angle shot",
    "Wide action shot",
    "Tracking shot",
]

PRESERVE_ITEMS = [
    "character identity", "facial structure", "outfit", "materials", "colors",
    "accessories", "environment", "lighting direction", "atmosphere",
    "cinematic color grading", "visual style",
]

AVOID_DEFAULT = (
    "redesigning the character, changing the outfit, changing the environment, changing the "
    "lighting style, adding extra characters, adding random objects, changing the face, cartoon "
    "style, CGI look, plastic skin, distorted anatomy, messy unreadable text, logos, watermarks, "
    "UI elements, or unrelated captions"
)

DURATION_CHOICES = (5, 8, 10, 12, 15)
MIN_DURATION = 3
MAX_DURATION = 120

# Story types the AI director supports, with narrative guidelines (not rigid formulas).
STORY_TYPES = {
    "cinematic_fantasy": ("Cinematic / fantasy",
                          "Calm world -> first sign of change -> character senses it -> tension builds -> "
                          "tease of the force -> escalation -> reveal -> iconic resolution."),
    "emotional": ("Emotional storytelling",
                  "Intimate everyday moment -> hint of loss or longing -> emotional low point -> memory or "
                  "connection -> small gesture -> release -> quiet, resonant ending."),
    "motivational": ("Motivational",
                     "Challenge -> struggle -> setback -> decision -> first progress -> persistence -> "
                     "transformation -> resolution that embodies the message."),
    "advertising": ("Advertising / marketing",
                    "Problem -> consequences -> discovery of the solution -> demonstration -> benefit -> "
                    "emotional payoff -> call to action (shown visually, no long text)."),
    "educational": ("Educational",
                    "Question -> context -> explanation (visual metaphor) -> demonstration -> "
                    "understanding -> application -> takeaway."),
    "documentary": ("Documentary",
                    "Establishing place -> subject in their routine -> observed details -> context -> "
                    "turning point -> human moment -> reflective closing image."),
    "product_showcase": ("Product showcase",
                         "Hero reveal -> design details -> materials/texture -> key feature in use -> second "
                         "feature -> lifestyle context -> final hero packshot."),
    "comedy": ("Comedy",
               "Normal situation -> setup of expectation -> complication -> escalation -> absurd peak -> "
               "twist -> punchline reaction."),
    "general": ("General narrative",
                "Setup -> inciting moment -> rising development -> turning point -> climax -> resolution."),
}

VISUAL_STYLES = [
    "Automatic",
    "Photorealistic cinematic film still",
    "Anamorphic widescreen film look",
    "Animated 3D feature-film style",
    "Hand-drawn 2D animation",
    "Anime",
    "Documentary realism",
    "Clean commercial product look",
    "Watercolor illustration",
    "Film noir black and white",
]

# ---- Original lesson template (legacy presets only; never injected into AI-generated projects)
# The universal 9-beat template, word for word from the lesson prompt.
TEMPLATE_BEATS = [
    {"title": "OPENING SILENCE", "shot": "Extreme wide shot",
     "action": "The character stands alone in the environment. The atmosphere is calm and cinematic."},
    {"title": "THE SHIFT BEGINS", "shot": "Medium shot",
     "action": "Wind, light, dust, rain, smoke, or atmosphere begins to move around the character."},
    {"title": "THE CHARACTER SENSES IT", "shot": "Close-up portrait",
     "action": "The character's eyes or expression subtly change as they notice something."},
    {"title": "SMALL DETAIL MOVES", "shot": "Detail shot",
     "action": "A small object, fabric, hand, ground texture, jewelry, water, or dust begins to react."},
    {"title": "TENSION BUILDS", "shot": "Low-angle or dramatic medium shot",
     "action": "The environment becomes heavier, stronger, or more unstable around the character."},
    {"title": "HIDDEN FORCE", "shot": "Wide shot",
     "action": "A mysterious shape, shadow, movement, light, or threat appears in the distance or background."},
    {"title": "ATMOSPHERE SURGES", "shot": "Side profile or cinematic angle",
     "action": "The character turns slightly as the atmosphere intensifies."},
    {"title": "THE REVEAL", "shot": "Wide action shot",
     "action": "The main visual event happens. Something powerful is revealed in the scene."},
    {"title": "HERO ENDING", "shot": "Low-angle hero shot",
     "action": "The character remains strong and visually iconic while the atmosphere surrounds them."},
]


TEMPLATE_CONCEPT = (
    "The character stands alone in their environment. They sense something changing. "
    "The atmosphere becomes more intense. Small details begin to move. A larger force or "
    "event appears in the distance. The character stays emotionally controlled as the scene "
    "builds toward a powerful final moment."
)

# What an uploaded reference image represents (user-selected; never guessed from the story).
REFERENCE_ROLES = {
    "character": "Character",
    "product": "Product",
    "environment": "Environment / location",
    "style": "Style reference",
}
