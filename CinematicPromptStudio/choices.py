"""Guided option lists for every shot decision, based on 01-Anatomy_of_Realism_Study_Notes.pdf.

Each option is (label, instruction, guide). The instruction is inserted into the prompt verbatim;
the guide explains when to pick it. Every instruction must pass core.validate_analysis.
"""
from __future__ import annotations

from core import FIELDS

# Field-level advice shown before an option is picked.
TIPS = {
    "subject": "Say who is visible and what makes them specific. Concrete age range, build and details replace the model's 'average' guess.",
    "wardrobe": "Texture-rich fabrics (wool, linen, embroidery, worn leather) give the camera detail to resolve and read as real.",
    "pose": "An action plus a glance tells the story without text: busy hands + a calm look at the phone = the ad's message.",
    "setting": "Name the place and two or three believable props. Imperfection belongs to the scene too: worn surfaces, dust, creased fabric.",
    "story": "Describe a specific emotional moment, not the word 'cinematic'. The model has no taste; you choose the intention.",
    "framing": "Shot size, lens and distance go together. An 85 mm close-up will not show a whole workshop in equal detail.",
    "placement": "Leave clean shadow space where the tagline and logo will be added in design afterwards. Never ask the model to render your text.",
    "camera_position": "Eye level reads honest and neutral; low angles add stature; high angles reduce it.",
    "sensor": "Full-frame 36x24 mm is the reference format that the lens table assumes. Medium format reads smoother and more premium.",
    "lens": "Focal length is shorthand for how far the camera stands from the face. 85 mm is the portrait sweet spot; 35 mm shows the environment.",
    "distance": "Keep distance consistent with lens and framing: an 85 mm head-and-shoulders shot is roughly 1.5-2 m away.",
    "aperture": "f/1.4-f/2 melts the background; f/5.6-f/8 keeps product and person both readable.",
    "focus": "Always add 'sharp focus on the eyes' for portraits: viewers judge a portrait by the eyes and it tells the model where the focal plane lives.",
    "shutter": "A proposed still setting. It hints at motion rendering; generators do not simulate a real shutter.",
    "iso": "Lower ISO reads clean; higher ISO implies available-light grain. A hint, not a physical simulation.",
    "white_balance": "Camera white balance sets the overall neutral point. Lights can still be warmer or cooler than it.",
    "key_source": "Light is ~70% of realism. Name a motivated source (window, sun, softbox, lamp) instead of 'dramatic lighting'.",
    "key_direction": "Use camera-left / camera-right. 45 degrees side and above eye level is the Rembrandt starting point.",
    "key_quality": "Large source relative to the subject = soft shadows; small or distant source = hard, crisp shadows.",
    "key_temperature": "Warm (tungsten, sunset) or cool (shade, moonlight, screens). Pick one number in Kelvin.",
    "pattern": "The shadow shape on the face: Rembrandt (dramatic), split (mysterious), loop (friendly), butterfly (glamour), broad/short.",
    "fill": "Fill decides how dark the shadow side is. 'Two stops below key' is clearer than 'dramatic lighting'.",
    "rim": "A rim only makes sense if a source can reach that edge. Choose 'no rim' when the reference has none.",
    "practicals": "Visible lamps or screens in frame can motivate background light and carry the story.",
    "shadows": "Shadows describe cheekbones, nose and jaw. Without them the face reads as a cut-out.",
    "catchlights": "A sharp, single natural catchlight from the key is a cinematic sign; perfectly symmetrical glassy catchlights look plastic.",
    "palette": "Cinema rarely uses fully saturated colour. Note 2-3 dominant colours and name them.",
    "grade": "Name the grade: teal shadows / warm skin is the most common, but bright and clean is also cinematic.",
    "skin": "Ask for life back: visible pores, fine lines, uneven tone, no retouching. Avoid 'flawless' and 'perfect skin'.",
    "materials": "Micro-contrast that reveals fabric weave, hair strands and metal scratches makes the frame feel photographed.",
    "grain": "Grain hides the too-clean digital look. Avoid '8K' and 'ultra HD' which push toward glossy AI art.",
    "atmosphere": "Haze, dust in a light beam or flare add depth, but only when the scene can motivate them.",
    "constraints": "State what must not happen: no text, no logos, clean anatomy, believable props.",
}

OPTIONS = {
    # ---------------- Scene ----------------
    "subject": [
        ("Business owner (portrait)", "A middle-aged business owner with a greying beard, weathered hands and an attentive, calm face; ordinary, believable features.", "Lesson exercise subject. Edit age, build and details to match your character."),
        ("Young professional", "A professional in their late twenties with natural, unstyled hair and a composed, confident expression.", "Clean corporate or tech feel."),
        ("Elderly craftsman", "An elderly craftsman with deep wrinkles, sun-weathered skin and strong, work-worn hands.", "Texture-rich face; ideal for Rembrandt or split lighting."),
        ("Clinic receptionist", "A friendly clinic receptionist in their thirties, mid-task, with a warm and approachable expression.", "Mojeeb's clinic segment from the 'next iterations' list."),
        ("Restaurant owner", "A restaurant owner in their forties, slightly flushed from a busy service, sleeves rolled up.", "Mojeeb's restaurant segment; pairs with warm practicals."),
        ("Product hero (no person)", "A single hero product placed upright and centred as the only subject; no people in frame.", "Use when the product is the star. Set skin to 'no skin' and catchlights to 'reflections only'."),
    ],
    "wardrobe": [
        ("Dishdasha + kumma", "A crisp white dishdasha and an embroidered kumma cap with fine visible stitching.", "From the lesson's Omani ad frame. White fabric needs protected highlights."),
        ("Vintage wool coat", "A vintage charcoal wool coat with visible weave and slight pilling over a plain dark shirt.", "The lesson prompt's texture-rich fabric."),
        ("Workwear", "Worn navy workwear overalls with faded seams, a few grease marks and rolled sleeves.", "Workshop and trades; imperfection adds life."),
        ("Smart casual", "A light linen shirt, slightly creased, sleeves folded once, no visible brand marks.", "Approachable commercial look."),
        ("Medical scrubs", "Plain teal medical scrubs with a lanyard and soft fabric creases.", "Clinic scenes."),
        ("No wardrobe (object)", "No wardrobe; the subject is an object, so styling applies only to its surface finish and placement.", "Pick this for product or still-life shots."),
    ],
    "pose": [
        ("Busy hands, calm glance", "Body angled three-quarters to camera, hands busy wiping grease with a cloth, glancing calmly toward a glowing phone beside him.", "Action + glance tells the ad story without text."),
        ("Direct gaze to lens", "Shoulders turned slightly away, head turned back to look directly into the lens with a relaxed, neutral mouth.", "Strong connection with the viewer; good for headshots."),
        ("Looking off-frame", "Three-quarter profile, eyes looking off-frame toward camera-left, thoughtful expression, hands relaxed.", "Cinematic, candid, gives look room."),
        ("On a phone call", "Holding a phone to the ear, slight smile, free hand gesturing mid-sentence.", "Communication / service stories."),
        ("Working at desk", "Seated at a desk, leaning slightly forward, typing, eyes on the screen.", "Office or reception scenes."),
        ("Product upright", "Product stands upright, angled 20 degrees toward camera-left to reveal front label and one side.", "Object orientation for product shots."),
    ],
    "setting": [
        ("Auto-repair workshop", "A cluttered auto-repair workshop with tool walls, an engine part on the bench and worn concrete floor, softly receding behind the subject.", "Lesson exercise setting."),
        ("Clinic front desk", "A busy clinic front desk with a computer monitor, appointment papers and a soft-focus waiting area behind.", "Clinic segment."),
        ("Restaurant at rush hour", "A restaurant during rush hour with steaming pass, plates and blurred staff moving in the background.", "Restaurant segment; adds energy."),
        ("Plain studio backdrop", "A plain mottled dark-grey canvas backdrop about two metres behind the subject.", "Classic portrait isolation."),
        ("Home office", "A small home office with bookshelves, a desk lamp and a window out of frame.", "Relatable everyday scene."),
        ("Tabletop surface", "A matte stone tabletop with a seamless warm-grey wall behind; no clutter.", "Product shots."),
    ],
    "story": [
        ("Calm in the chaos", "Quiet confidence in a busy moment: everything demands his attention, yet he is calm because the call is being handled.", "The Mojeeb promise: 'answers when nobody can'."),
        ("Dramatic & introspective", "A moody, introspective moment of reflection after a long day; serious but not sad.", "Pairs with Rembrandt or split lighting."),
        ("Warm & welcoming", "Warm, welcoming hospitality; the viewer feels greeted and looked after.", "Commercial, friendly; pairs with loop lighting."),
        ("After hours", "An after-hours moment alone in the workplace, quiet and slightly mysterious.", "Lesson's split-lighting iteration."),
        ("Pride in craft", "Pride and focus in skilled work; the hands and tools tell the story.", "Craft and trade stories."),
        ("Premium product", "A premium, desirable product presented with calm, confident simplicity.", "Product hero."),
    ],
    # ---------------- Composition ----------------
    "framing": [
        ("Close-up portrait", "Close-up portrait framed from mid-chest to just above the head, face filling the upper third of the frame.", "Lesson default with 85 mm; faces dominate."),
        ("Head-and-shoulders", "Head-and-shoulders crop with a little space above the head and the shoulders cut by the frame edges.", "Classic portrait / profile photo."),
        ("Medium shot", "Medium shot from the waist up, hands and the immediate prop visible.", "Shows action and hands; 50 mm."),
        ("Environmental wide", "Environmental wide shot, full body visible and occupying about one third of the frame height, surroundings clearly readable.", "35 mm, f/4 version where the place matters."),
        ("Tight headshot", "Tight headshot from chin to forehead, crop slightly into the top of the head.", "135 mm compression; intense."),
        ("Product hero crop", "Product fills about sixty percent of the frame with even margins and a little space above.", "Product shots."),
    ],
    "placement": [
        ("Left third + text space right", "Subject on the left third, eyes on the upper-third line, clean dark negative space on the right for a tagline and logo added later.", "Lesson brief: shadow space for design text."),
        ("Right third + text space left", "Subject on the right third, looking into the frame, clean negative space on the left for later typography.", "Mirror of the above; look room into frame."),
        ("Centred, symmetrical", "Subject centred with balanced headroom and symmetrical background elements.", "Direct, iconic, confrontational."),
        ("Text space at top", "Subject in the lower two thirds with a calm, uncluttered upper band for a headline.", "Stories / Reels covers (9:16)."),
        ("Leading lines", "Subject on a third, with workbench and shelf lines leading the eye toward the face.", "Environmental frames."),
    ],
    "camera_position": [
        ("Eye level, straight", "Camera at the subject's eye level, level horizon, about 20 degrees off the subject's nose axis.", "Neutral and honest; most portraits."),
        ("Slightly low", "Camera slightly below eye level, tilted up about 10 degrees, lending quiet stature.", "Confidence and authority."),
        ("Slightly high", "Camera slightly above eye level, tilted down about 10 degrees, gentle and approachable.", "Softer, flattering for close-ups."),
        ("Over-the-shoulder", "Camera behind and to one side at shoulder height, foreground shoulder softly out of focus.", "Adds depth and voyeuristic intimacy."),
        ("Product 30 degrees down", "Camera 30 degrees above the tabletop looking down toward the product front.", "Standard product angle."),
    ],
    # ---------------- Camera & optics ----------------
    "sensor": [
        ("Full-frame digital", "Full-frame 36x24 mm digital capture target with clean, modern colour.", "Reference format for all lens values here."),
        ("35mm film (Portra 400)", "35mm film capture target emulating Kodak Portra 400, with natural skin tones and gentle highlight rolloff.", "Lesson's 'medium' suggestion; warm, organic."),
        ("Medium format", "Medium-format 44x33 mm digital capture target with smooth tonal gradation and subtle depth.", "Premium, editorial, smooth."),
        ("Cinema camera (Super 35)", "Super 35 cinema-camera capture target with a soft log-to-Rec.709 film look.", "Movie-still feel; 16:9 and 2.39:1."),
    ],
    "lens": [
        ("85mm portrait", "85 mm full-frame portrait lens with natural facial proportions and gentle background compression.", "Portrait sweet spot: flattering face, soft background."),
        ("35mm environmental", "35 mm full-frame lens showing the environment, with mild perspective stretch kept away from the face.", "Person in their workshop/clinic; establishing shots."),
        ("50mm normal", "50 mm full-frame lens with a neutral, close-to-human-eye perspective.", "Documentary, half-body."),
        ("135mm telephoto", "135 mm full-frame telephoto with strong compression and an isolated subject.", "Tight headshots; candid 'paparazzi' feel."),
        ("24mm wide", "24 mm full-frame wide lens with expansive space; keep faces away from frame edges to limit distortion.", "Dramatic establishing shots only; distorts close faces."),
        ("100mm macro", "100 mm full-frame macro lens with crisp close-focus detail.", "Product details, textures."),
    ],
    "distance": [
        ("1.8 m (85mm close-up)", "Camera about 1.8 m from the subject, natural facial proportions, background compressed.", "Matches 85 mm close-up / head-and-shoulders."),
        ("1.2 m (50mm medium)", "Camera about 1.2 m from the subject, neutral perspective for a waist-up frame.", "Matches 50 mm medium shot."),
        ("3 m (35mm wide)", "Camera about 3 m from the subject so the surroundings read clearly without facial distortion.", "Matches 35 mm environmental."),
        ("3.5 m (135mm headshot)", "Camera about 3.5 m from the subject, strong compression, background pulled close.", "Matches 135 mm tight headshot."),
        ("0.6 m (product)", "Camera about 0.6 m from the product, perspective kept straight and undistorted.", "Tabletop product."),
    ],
    "aperture": [
        ("f/1.8 shallow", "f/1.8 for very shallow depth of field: eyes sharp, background melts into soft bokeh.", "Cinematic portraits (lesson prompt)."),
        ("f/1.4 ultra shallow", "f/1.4 for extremely shallow depth of field with a creamy, dreamy background.", "Maximum isolation; careful focus needed."),
        ("f/2.8 balanced", "f/2.8 keeping the full face sharp while the background softens but stays recognisable.", "Face fully sharp, setting still reads."),
        ("f/4 environmental", "f/4 keeping the subject and nearby setting readable with a gently soft distance.", "Lesson's wider 35 mm, f/4 iteration."),
        ("f/8 deep", "f/8 for deep focus: product and person, or the whole scene, sharp together.", "Product + person, group shots."),
    ],
    "focus": [
        ("Sharp on the eyes", "Sharp focus on the eyes, gradual falloff through the ears and shoulders, background softly blurred.", "Lesson rule: always add 'sharp focus on the eyes'."),
        ("Near eye", "Critical focus on the near eye, the far eye slightly softer, smooth falloff behind.", "Very shallow apertures and three-quarter poses."),
        ("Eyes + hands", "Focus on the eyes with the busy hands still readable, background workshop softly blurred.", "When the action carries the story; use f/2.8-f/4."),
        ("Product label", "Sharp focus on the product's front label, gentle falloff toward the back edges.", "Product shots."),
        ("Deep focus", "Deep focus with subject and background equally readable, no artificial bokeh.", "Pairs with f/8 and wider lenses."),
    ],
    "shutter": [
        ("1/160 s frozen", "1/160 s, freezing the subject crisply with no motion blur.", "Safe handheld portrait default."),
        ("1/60 s slight motion", "1/60 s, the subject sharp while moving hands show a hint of natural motion blur.", "Adds life to busy hands."),
        ("1/500 s action", "1/500 s, freezing fast action and flying particles cleanly.", "Steam, splashes, quick movement."),
        ("1/15 s background drag", "1/15 s on a tripod, still subject sharp while people moving in the background blur.", "Busy restaurant / clinic energy."),
    ],
    "iso": [
        ("ISO 100 clean", "ISO 100, clean exposure, highlights protected, deep but detailed shadows.", "Studio or bright daylight."),
        ("ISO 400 natural", "ISO 400, exposure for the face, highlights protected, shadow detail retained.", "Window light interiors; matches Portra 400."),
        ("ISO 800 available light", "ISO 800, available-light exposure with a little natural noise, shadows held just above black.", "Dim interiors, moody scenes."),
        ("ISO 1600 low light", "ISO 1600, low-light exposure with visible fine noise, highlights from practicals allowed to bloom slightly.", "Night, after-hours."),
    ],
    "white_balance": [
        ("5600K daylight", "Camera white balance 5600K, neutral tint, daylight reads clean and tungsten practicals read warm.", "Window or sun key."),
        ("4800K slightly warm", "Camera white balance 4800K with neutral tint, making a daylight key read slightly cool and skin natural.", "Mixed light, gentle cool ambient."),
        ("3200K tungsten", "Camera white balance 3200K, neutral tint, tungsten key reads neutral and daylight leaks read blue.", "Tungsten-lit interiors, night."),
        ("6500K warm shift", "Camera white balance 6500K, slight magenta tint, everything renders a little warmer.", "Golden, sunny, nostalgic feel."),
    ],
    # ---------------- Lighting ----------------
    "key_source": [
        ("Window light", "A single large window as the key, diffused by a sheer curtain, roughly 1.5 m wide.", "Natural, soft, believable; lesson exercise."),
        ("Large softbox", "A 120 cm octabox softbox as the single key.", "Controlled studio softness."),
        ("Hard direct sun", "Hard direct sunlight through an open doorway as the key, small apparent source.", "Crisp shadows, summer heat."),
        ("Bare bulb / lamp", "A single bare tungsten bulb hanging overhead as the key.", "Gritty, intimate, after hours."),
        ("Overcast daylight", "Open overcast sky as a huge soft key from above and in front.", "Even, gentle outdoor light."),
        ("Phone screen glow", "A phone screen as the only key, tiny and cool, lighting the face from below and close.", "Night, intimate; very low-key."),
    ],
    "key_direction": [
        ("45° camera-left, high", "Key 45 degrees camera-left, about 30 degrees above eye level, roughly 1.5 m from the subject.", "Rembrandt starting point."),
        ("45° camera-right, high", "Key 45 degrees camera-right, about 30 degrees above eye level, roughly 1.5 m from the subject.", "Rembrandt from the other side."),
        ("90° camera-left (side)", "Key 90 degrees camera-left at eye level, roughly 1.2 m from the subject.", "Split lighting."),
        ("30° camera-right", "Key 30 degrees camera-right, slightly above eye level, roughly 1.5 m away.", "Loop lighting."),
        ("High, in front", "Key directly in front of the face and high above the lens, angled down about 40 degrees.", "Butterfly / Paramount."),
        ("Behind (backlight)", "Key behind the subject camera-right, about 150 degrees from the lens, at head height.", "Backlit silhouettes and halos."),
    ],
    "key_quality": [
        ("Soft, gentle falloff", "Soft key with gradual shadow edges, gentle wrap onto the shadow cheek and smooth falloff.", "Large source close to the subject."),
        ("Semi-soft", "Semi-soft key with defined but slightly feathered shadow edges and moderate falloff.", "Balanced, commercial."),
        ("Hard, crisp shadows", "Hard key with crisp, sharply defined shadow edges and no wrap.", "Small or distant source; dramatic."),
        ("Fast falloff", "Soft key with fast falloff, light dropping off quickly across the face into the background.", "Moody, chiaroscuro."),
    ],
    "key_temperature": [
        ("5600K daylight", "Key at about 5600K, neutral daylight character.", "Window, sun, daylight softbox."),
        ("3200K tungsten", "Key at about 3200K, warm tungsten character.", "Lamps, bulbs, practicals."),
        ("4000K warm-neutral", "Key at about 4000K, slightly warm neutral character.", "Mixed interior light."),
        ("2700K golden", "Key at about 2700K, deep golden warmth.", "Sunset, candle, nostalgic."),
        ("7000K cool", "Key at about 7000K, cool blue character.", "Shade, moonlight, screens."),
    ],
    "pattern": [
        ("Rembrandt", "Rembrandt lighting: lit side bright, shadow side dark except a small triangle of light under the eye on the shadow cheek, no wider than the eye.", "Dramatic, classic, painterly. Key 45° side + high."),
        ("Split", "Split lighting: exactly half the face lit and half in shadow, divided along the nose.", "Mysterious, hard, thriller. Key at 90°."),
        ("Loop", "Loop lighting: a small nose shadow loops toward the cheek without joining the cheek shadow.", "Natural, friendly, commercial. Key ~30°."),
        ("Butterfly / Paramount", "Butterfly lighting: a small butterfly-shaped shadow directly under the nose, cheekbones defined evenly.", "Glamour, beauty, fashion. Key high and in front."),
        ("Short lighting", "Short lighting: the side of the face turned away from camera is lit, the near side falls into shadow.", "Slims the face and adds mood."),
        ("Broad lighting", "Broad lighting: the side of the face turned toward camera is lit, the far side in gentle shadow.", "Widens and opens the face; friendly."),
    ],
    "fill": [
        ("No fill, negative fill", "No added fill; black negative fill on the shadow side keeps it about three stops below the key.", "Deep shadows, low-key drama."),
        ("Gentle fill (2 stops)", "Gentle white bounce fill from camera-right, about two stops below the key.", "Shadow side readable but still shaped."),
        ("Soft fill (1 stop)", "Soft frontal fill about one stop below the key for low contrast.", "Bright, commercial, friendly."),
        ("Ambient bounce only", "No added fill; only natural ambient bounce from the room, about two and a half stops below the key.", "Realistic interiors."),
    ],
    "rim": [
        ("No rim", "No separate rim light; subject separates from the background through tone and focus only.", "Match references without an edge light."),
        ("Phone glow as subtle rim", "Warm practical glow from the phone screen as a subtle rim on the near cheek and hand, very low level.", "Lesson exercise: story-carrying accent."),
        ("Cool hair light", "A cool hair light from behind camera-right, one stop below key, tracing hair and shoulder edges.", "Separates dark hair from dark backgrounds."),
        ("Warm kicker", "A warm kicker from behind camera-left at 3200K, one stop below key, on jaw and ear edge.", "Adds dimension and warmth."),
        ("Window backlight edge", "Daylight from a window behind the subject creating a soft bright edge on the hair and shoulders.", "Natural, airy."),
    ],
    "practicals": [
        ("None visible", "No visible practical lights; background lit only by spill from the key.", "Clean, minimal frames."),
        ("Warm lamps in background", "Two dim warm tungsten lamps in the background, out of focus, adding small pools of light.", "Cosy depth and colour contrast."),
        ("Phone screen glow", "A small desk phone screen glowing softly beside the subject, the only practical in frame.", "Lesson exercise: the phone carries the story."),
        ("Fluorescent tubes", "Overhead fluorescent tubes in the deep background, slightly green-cool and out of focus.", "Workshop, garage, clinic realism."),
        ("Neon / signage glow", "Out-of-focus coloured neon signage glow in the deep background, no readable letters.", "Night city, restaurants."),
    ],
    "shadows": [
        ("Deep shadow side", "Deep shadows on one side of the face, soft-edged, shadow detail barely retained, high contrast.", "Lesson prompt: chiaroscuro, sculpted face."),
        ("Medium contrast", "Medium contrast with readable shadow detail, clear direction and grounded contact shadows.", "Commercial realism."),
        ("Low contrast, open", "Low contrast with open, airy shadows and gentle shape.", "Bright, high-key, friendly."),
        ("Hard graphic shadows", "Hard graphic shadows with sharp edges and dense blacks; shapes cast across face and wall.", "Hard sun or bare bulb."),
    ],
    "catchlights": [
        ("Single natural from key", "A single natural catchlight in each eye at the 10 o'clock position, matching the window key.", "Lesson: 'sharp, single natural catchlight from the key'."),
        ("Single at 2 o'clock", "A single natural catchlight in each eye at the 2 o'clock position, matching a camera-right key.", "Matching a camera-right key."),
        ("Small, low-key", "Small, dim catchlights from the key, eyes mostly in shadow but alive.", "Very moody setups."),
        ("Round, top-centre", "Round catchlights at the top centre of each eye from a high frontal source.", "Butterfly lighting."),
        ("Reflections only (no eyes)", "No visible eyes; controlled soft reflections along the product edges consistent with the key.", "Product / object shots."),
    ],
    # ---------------- Color & finish ----------------
    "palette": [
        ("Muted earthy", "Muted earthy palette: warm skin, olive grey and dusty brown, low saturation.", "Lesson default; cinematic restraint."),
        ("Teal & warm skin", "Restricted palette of deep teal shadows, warm amber skin and off-white highlights, moderate saturation.", "Most common cinematic look."),
        ("Clean & bright", "Clean bright palette of white, soft blue and natural skin, moderate saturation.", "Healthcare, tech, friendly brands."),
        ("Warm golden", "Warm golden palette of honey, amber and cream, gentle saturation.", "Hospitality, nostalgia."),
        ("Monochrome-leaning", "Near-monochrome palette of charcoal, cool grey and skin tone, very low saturation.", "Serious, editorial."),
    ],
    "grade": [
        ("Teal-orange undertone", "Subtle teal-orange grade: cool teal shadows, warm skin midtones, lifted black point, soft highlight rolloff.", "Lesson exercise; fits a blue brand with warm skin."),
        ("Natural filmic", "Natural filmic grade with gentle S-curve, slightly lifted blacks and soft highlight rolloff.", "Realistic, unobtrusive."),
        ("High-contrast moody", "Moody grade with deep blacks, compressed highlights and a strong S-curve.", "Low-key drama."),
        ("Bright & airy", "Bright airy grade with clean whites, open shadows and a gentle low-contrast curve.", "High-key commercial."),
        ("Warm vintage", "Warm vintage grade with faded blacks, creamy highlights and slightly yellowed midtones.", "Nostalgic film look."),
    ],
    "skin": [
        ("Natural detailed", "Highly detailed natural skin texture, visible pores, fine lines, uneven tone, no skin smoothing or retouching.", "Lesson core: asks for life back."),
        ("Weathered & stubble", "Weathered skin with visible pores, light stubble and greying beard, fine wrinkles and slight sweat sheen.", "Lesson exercise; workers and craftsmen."),
        ("Soft but real", "Soft clean skin with visible fine pores and natural tonal variation, lightly groomed, not airbrushed.", "Beauty/commercial without plastic."),
        ("Freckles & blemishes", "Natural freckles and small blemishes, peach fuzz visible in the light, uneven tone retained.", "Young subjects, authenticity."),
        ("No skin (object)", "No skin in frame; organic texture comes from materials and surfaces instead.", "Product / object shots."),
    ],
    "materials": [
        ("Fabric & hair micro-contrast", "Crisp micro-contrast revealing fabric weave, embroidery stitches and individual hair strands.", "Portraits with textured clothing."),
        ("Worn workshop surfaces", "Grease on hands, scratched metal tools, worn wood bench and dust on surfaces.", "Imperfection belongs to the scene."),
        ("Clean clinical surfaces", "Smooth clean surfaces with soft reflections, slight fingerprints on glass and gentle paper texture.", "Clinic and office."),
        ("Product finish", "Accurate product finish: fine brushed-metal grain, soft glass reflections and crisp label edges.", "Product shots."),
    ],
    "grain": [
        ("Subtle 35mm grain", "Subtle 35mm film grain, natural micro-contrast, gentle optical softness, no over-sharpening.", "Lesson default; hides the too-clean digital look."),
        ("Clean digital", "Clean digital capture with very fine sensor noise, natural sharpness, no artificial sharpening.", "Modern commercial looks."),
        ("Heavy film grain", "Pronounced film grain with soft optics and slight halation around highlights.", "Gritty, nostalgic, documentary."),
        ("Fine Portra grain", "Fine Kodak Portra 400 style grain, smooth tonal transitions and organic sharpness.", "Warm portrait film feel."),
    ],
    "atmosphere": [
        ("Clear air", "Clear air with no added haze, fog or flare.", "Match-reference default; don't invent effects."),
        ("Dust in light beam", "Light dust particles visible in the window light beam, subtle and low density.", "Workshops, attics, old rooms."),
        ("Light haze", "Gentle atmospheric haze adding depth to the background, low strength.", "Cinematic depth."),
        ("Soft flare / bloom", "Soft warm lens flare and gentle highlight bloom from the backlight, low strength.", "Golden hour, dreamy."),
        ("Steam", "Light steam rising softly in the background, motivated by cooking.", "Restaurant kitchens."),
    ],
    "constraints": [
        ("No text, clean anatomy", "Photorealistic, not retouched; no text, no logos, no watermarks; natural hands with five fingers; believable props.", "Lesson rule: never ask the model to render your logo or text."),
        ("Keep identity & wardrobe", "Preserve the reference person's face shape, age appearance and wardrobe; no text or logos; clean anatomy.", "When a reference identity matters (no guarantee of 100% match)."),
        ("Product integrity", "Keep the product's shape, proportions and colours exact; no invented labels or text; no extra objects.", "Product shots."),
        ("Ad text space", "Keep the negative space free of objects and text for later design; no logos; clean hands and props.", "Ads where typography is added later."),
    ],
}

DEFAULT_AVOID = [
    "8K, ultra HD or glossy over-sharpened AI-art look",
    "airbrushed, waxy or plastic skin",
    "flat frontal on-camera-flash lighting",
    "glassy, perfectly symmetrical catchlights",
    "everything equally sharp or cut-out look",
    "over-saturated HDR colour",
    "melted hands, warped faces or objects",
    "gibberish text, watermarks and invented logos",
]

# After changing one decision, these related decisions should be checked for consistency.
RELATED = {
    "framing": ["lens", "distance", "placement"],
    "lens": ["distance", "framing", "focus", "aperture"],
    "distance": ["lens", "framing"],
    "aperture": ["focus", "lens"],
    "focus": ["aperture"],
    "key_source": ["key_quality", "key_temperature", "catchlights"],
    "key_direction": ["pattern", "shadows", "catchlights", "fill"],
    "key_quality": ["key_source", "shadows"],
    "key_temperature": ["white_balance", "palette"],
    "white_balance": ["key_temperature", "grade"],
    "pattern": ["key_direction", "shadows", "catchlights"],
    "fill": ["shadows"],
    "rim": ["practicals", "key_direction"],
    "practicals": ["rim", "palette"],
    "palette": ["grade"],
    "grade": ["palette", "grain"],
    "subject": ["wardrobe", "skin", "pose"],
    "setting": ["practicals", "materials"],
}

# Coherent starting kits taken from the lesson, applied in one click.
PRESETS = {
    "Lesson: Rembrandt close-up (85mm f/1.8)": {
        "framing": "Close-up portrait", "lens": "85mm portrait", "distance": "1.8 m (85mm close-up)",
        "aperture": "f/1.8 shallow", "focus": "Sharp on the eyes", "key_source": "Window light",
        "key_direction": "45° camera-left, high", "key_quality": "Soft, gentle falloff", "pattern": "Rembrandt",
        "fill": "No fill, negative fill", "shadows": "Deep shadow side", "catchlights": "Single natural from key",
        "palette": "Muted earthy", "grade": "Teal-orange undertone", "grain": "Subtle 35mm grain"},
    "After hours: split light": {
        "key_direction": "90° camera-left (side)", "key_quality": "Hard, crisp shadows", "pattern": "Split",
        "fill": "No fill, negative fill", "shadows": "Hard graphic shadows", "catchlights": "Small, low-key",
        "story": "After hours", "grade": "High-contrast moody", "iso": "ISO 1600 low light"},
    "Wide environmental (35mm f/4)": {
        "framing": "Environmental wide", "lens": "35mm environmental", "distance": "3 m (35mm wide)",
        "aperture": "f/4 environmental", "focus": "Eyes + hands", "placement": "Leading lines"},
    "Friendly commercial (loop)": {
        "key_source": "Large softbox", "key_direction": "30° camera-right", "key_quality": "Semi-soft",
        "pattern": "Loop", "fill": "Soft fill (1 stop)", "shadows": "Low contrast, open",
        "catchlights": "Single at 2 o'clock", "palette": "Clean & bright", "grade": "Bright & airy",
        "story": "Warm & welcoming", "grain": "Clean digital"},
}


def options_for(key):
    return OPTIONS.get(key, [])


def find_option(key, label):
    for option in OPTIONS.get(key, []):
        if option[0] == label:
            return option
    return None


def option_record(key, label):
    """A validated-shape field record for one option, marked as the user's choice."""
    option = find_option(key, label)
    if option is None:
        raise KeyError(f"No option {label!r} for {key}.")
    _, instruction, guide = option
    return {"observation": "No reference analyzed for this choice; selected from the guided option list.",
            "choice": instruction, "basis": "user",
            "reason": f"Chosen from guided options ({label}). {guide}"}


def build_guided_plan():
    """A complete plan made of each field's first option, ready for the user to change."""
    fields = {key: option_record(key, OPTIONS[key][0][0]) for key in FIELDS}
    return {"summary": "Guided shot plan built from option lists, not from an analyzed image. Change any decision in 33 shot choices.",
            "fields": fields, "avoid": list(DEFAULT_AVOID),
            "uncertainties": ["No reference image was analyzed; every choice is a selected recreation setting."]}
