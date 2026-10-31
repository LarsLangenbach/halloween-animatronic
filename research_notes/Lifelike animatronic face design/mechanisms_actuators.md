# Mechanisms and actuators for a lifelike animatronic face (hobby scale, October 2026)

Scope: the mechanical side only. Animation software, easing, lip-sync tools and control-level jitter were covered in an earlier round and are not repeated here. Local sources are Will Cogley's Patreon files already in this repo (private; never share). Their paths are relative to this notes file. Where a finding comes from a search-engine summary rather than a page I read in full, it says "(search summary)".

Project facts that frame the notes: the team is now building Cogley's Robot Head α2.0.33 as he designed it, including his 4-servo brows with TPU brow bars (PLAN D15, D17). The servo count is 17 × MG90S plus 2 × MG996R for the jaw. The head sits on a fixed pedestal with no neck joint (PLAN Q17, D25). Power is a 20 A buck at 5.30 V ([PLAN.md](../../docs/PLAN.md), Q19).

## 1. Lips and mouth: corners (AU12/AU15), upper-lip raise and sneer (AU10), lower lip, pucker and press, and decoupling the lips from the jaw

### Takeaway
Cogley's α2.0.33 mouth already covers jaw, upper lip, lower lip and two corner servos per side (up/down plus in/out) and a tongue: 12 PWM channels, with one spare (EXA) left unused. What it lacks, compared with pro and research faces, is a dedicated sneer or nose-root lift (AU10 on the side of the nose), a real pucker or lip-press, and a cheek lift. The cheapest high-value additions are an AU10 snarl pull per side and using the spare channel. Corners are the hardest spot on a skin. Use embedded anchors with a cable pull you can adjust, and support the skin on a rigid underskull so the pull does not twist the face.

### Cited Findings
**What Cogley's mouth provides**
- The α2.0.33 mouth code defines 12 servos: JL and JR (jaw left and right), LUL and LUR (upper lip left and right), LLL and LLR (lower lip left and right), CUL, CUR, CLL and CLR (corner upper and corner lower, each side), TON (tongue) and EXA (spare). Built-in poses: mouth_open/closed, lips_up/down, tongue_up/down, smile, frown, wide and narrow. "Smile" and "frown" move only CUL and CUR. "Wide" also moves the lower corner servos, CLL and CLR. — [Cogley α2.0.33 Code/Mouth.py (local Patreon file)](../../inputs/reference/head_a2.0.33/Code/Mouth.py)
- The mouth STEP assembly contains 9 × MG90S and 2 bodies that look like MG996R jaw servos. — [inputs/reference/README.md](../../inputs/reference/README.md)
- The project plan counts the mouth board as driving 2 × MG996R jaw servos, 4 lip, 4 cheek (corner) and 1 tongue servo, plus one spare. — [docs/PLAN.md](../../docs/PLAN.md)
- Cogley's earlier mouth (2020) used nine servos. Between them they moved the jaw up and down, pushed and pulled the mouth corners, raised and lowered the lips, and moved the tongue. He simplified the mechanics to focus on a text-to-phoneme-to-mouth-shape driver. — [Hackaday, 2020](https://hackaday.com/2020/04/30/this-animatronic-mouth-mimics-speech-with-servos/)
- In that earlier design the lips were shaped with guitar wire soldered to wires that ran to servos further back in the head (search summary). — [Planet Arduino](http://www.planetarduino.org/?cat=1871)
- Hackster reported two servos on each linkage cheek (corner) assembly, giving up, down, in and out motion, and a pair of MG996R on the jaw (search summary). — [Hackster.io](https://www.hackster.io/news/will-cogley-s-animatronic-mouth-responds-to-his-typing-2e4d892f453c)

**How research and pro faces move the mouth**
- A 2026 RSS paper (BAAI and Tsinghua) uses a spatial four-bar linkage with vertical motion for each of the upper and lower lips. The mouth corners use a five-bar mechanism that can raise, move sideways and pull down. The jaw is a four-bar linkage. — [Zhang et al., arXiv 2607.11688 (RSS 2026)](https://arxiv.org/html/2607.11688)
- A 2026 receptionist head (National University of Singapore and University of Moratuwa) has 9 mouth DoF: 8 lip servos and 2 jaw motors. A four-bar at each mouth corner moves it in a vertical plane. — [arXiv 2607.17042 (AIM 2026)](https://arxiv.org/html/2607.17042)
- Garner Holt's 2017 expressive Lincoln head has 45 actuators, 12 of them for the lips. — [MiceChat, 2017](https://micechat.com/168204-blurring-mechanical-line-ghps-new-animatronic-head-offers-glimpse-future-expressive-characters/)
- The Eva head drives AU10 (upper lip), AU11 (nasolabial deepening), AU12, AU15 and AU20 (mouth corners) and AU16 (lower lip) with steel wires pulled by servo banks. — [Faraj et al., HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)
- The A-Lab pneumatic android (14 actuators) has mouth corner up, mouth corner back, lip shrink, lips open and jaw down. It has no nose-root actuator, so AU10 correlated with nothing and was dropped. Its single mouth-corner-up actuator also correlated with AU6, AU7 and AU9, so smile, squint and nose wrinkle come out entangled. — [arXiv 2412.13641](https://arxiv.org/html/2412.13641v1)

**Sneer, snarl and lip rigs from creature-FX builders**
- In a wolf-head build, two lip-lift (snarl) servos run through brass guide tubes, and a separate servo gives an upper-lip twitch "for realistic speaking parts". A lower servo moves an arm with a roller that lifts the nose. That one servo gives a breathing twitch, a sniff, or a full snarl that lifts the lip off the upper teeth and gums. A full nose raise is about double a snarl's travel. — [Stan Winston School forum, wolf head](https://forums.stanwinstonschool.com/discussion/comment/7448)
- In the same thread, Chris Ellerby (forum admin) suggests lip rigs that open the lips as the jaw opens: extra motion without extra servos. The builder cites a video where the face was not well supported on the underskull and twisted. — [Stan Winston School forum](https://forums.stanwinstonschool.com/discussion/comment/7448)
- For smile and frown, Ellerby advises pulling a cable, like a bicycle brake cable or a lightweight RC aeroplane cable, rather than linking the servo directly to the skin, so the pull angle can be tuned. He also advises a sculpted form under the skin to anchor against. He disagrees that a lip-lifter cable must pull into a smile whenever the mouth opens, since opening "does not generally increase the circumference of the mouth much". In that build, too much arm travel pulled the skin off the arm, too little did not read, and some arm lengths made the skin bind. — [Stan Winston School forum, smile/frown](https://forums.stanwinstonschool.com/discussion/11383/smile-frown-mechanism-for-canid-wolf-anthro-heads)
- Stan Winston School's paid "How To Build An Animatronic Head Part 4" (Craig Caton-Largent) covers lip cables, tabs and lip servos (search summary; contents not public). — [SWS forum listing](https://forums.stanwinstonschool.com/discussion/3347/now-on-demand-how-to-build-an-animatronic-head-part-4)

**Anchoring the corners to silicone**
- Mouth corners and eyelids are the most common failure points on skins, and anchors are usually embedded during molding (search summary). — [Animatronics Street](https://animatronicsstreet.com/animatronics-foundations/materials-and-skins/)
- Perforation-type anchors (inspired by skin ligaments) let external actuators pull the mouth corners into a smile. The study used 5 mm anchors on the rod parts and 3 mm anchors in the silicone and dermis layers, and examined how anchor diameter affects holding strength. — [Kawai et al., Cell Reports Physical Science 2024](https://www.cell.com/cell-reports-physical-science/fulltext/S2666-3864(24)00335-7)
- Hobby options from the SWS forum: fabric pads glued to the silicone with silicone adhesive, threaded studs with fabric backing embedded in the skin (untried by the poster), or magnets. Magnets may stress the skin and collect metal particles that discolour it, and closely spaced lip magnets snap to each other. — [SWS forum, attaching control cables](https://forums.stanwinstonschool.com/discussion/5676/attaching-control-cables-to-silicone-mask)
- A robotics-skin patent makes the force-receiving mouth component harder than the surrounding skin, so it wears better and transfers motion better. — [US7740953B2](https://patents.google.com/patent/US7740953)

### Inferences
- Cogley's mouth already has the corner DoF most hobby faces lack: two servos per corner give AU12 (up and out), AU15 (down) and AU20 (wide). The biggest missing expressive unit is AU10, the upper-lip and nose-side lift that makes a sneer or snarl. For a Frankenstein's monster, a snarl is arguably worth more than any other addition. One MG90S per side pulling a Bowden cable up beside the nose (the wolf-head roller-arm or guide-tube approach) is cheap. The spare EXA channel can drive one side, or both sides together through a split cable, as Eva does.
- Lip motion is decoupled from the jaw either by mounting the lower-lip and lower-corner actuators on the jaw itself (Eva's "bottom bank" rides on the jaw) or by routing cables close to the jaw hinge axis, so opening barely changes their length. Check which one Cogley's assembly does: whether LLL, LLR, CLL and CLR ride on the jaw is not stated in the sources read here.
- Pucker (AU18) and lip press (AU24) need a drawstring-like inward pull round the lips or a lip-roll mechanism. No hobby source found shows one. Cogley's "narrow" pose (corners in) is the nearest he offers.

### Gaps
- Whether Cogley's lower-lip and lower-corner servos ride on the jaw or on the skull: not read from the STEP in this round. A quick look at the assembly would settle it.
- What EXA was meant for: Cogley's code gives no comment.
- No published hobby mechanism for pucker or lip press was found.

## 2. Cheeks and nasolabial fold: cheek raise (Duchenne smile, AU6), squint (lower lid raise, AU7) and nose wrinkle (AU9)

### Takeaway
A smile reads as real (Duchenne) when the cheek rises and the lower lid comes up with it. Research faces drive the cheek and nose with strings (tendons) and give the lower lid its own DoF. Cogley's head already has independent lower lids, so a squint is a software change. A cheek-raise tendon per side plus a nose-wrinkle pull are the hardware additions, and his CheekBone band gives them a rigid place to anchor.

### Cited Findings
- The Morpheus face (RSS 2025) uses hybrid actuation. Rigid linkages drive the eyes and the key mouth areas for precise, emotionally important motion. Strings drive the nose and cheeks, where they are compact and suit subtle microexpressions. The authors say rigid-only designs are hard to fit, and tendon-only designs are hard to control. — [Zhang et al., arXiv 2507.16645](https://arxiv.org/abs/2507.16645)
- The same paper says only the upper lid moves in a blink, but the lower lid rises when the orbicularis oculi contracts, so the lower lid needs its own DoF (search summary of the PDF). — [arXiv 2507.16645](https://arxiv.org/pdf/2507.16645)
- Android actuator tables list "raising the lower eyelid" and "raising the cheek" as separate units. The Affetto table separates the middle cheek, the lower cheek pulled to the side, and the mouth corner raise (search summary). — [PMC8019968 table](https://pmc.ncbi.nlm.nih.gov/articles/PMC8019968/table/T1)
- Eva covers AU6 (cheek raiser), AU7 (lid tightener), AU9 (nose wrinkle) and AU11 (nasolabial deepener) with Bowden wires, each servo pulling a symmetric left and right pair. — [HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)
- A robotic-creature patent pushes the lower lid up to show a smile (search summary). — [US10120386](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10120386)
- On the A-Lab android, the mouth-corner-up actuator correlated with AU6, AU7 and AU9 at once. Smile, squint and nose wrinkle were mechanically entangled. — [arXiv 2412.13641](https://arxiv.org/html/2412.13641v1)
- Garner Holt's Lincoln head has eye-area and nose creases and wrinkling that changes with expression. — [MiceChat, 2017](https://micechat.com/168204-blurring-mechanical-line-ghps-new-animatronic-head-offers-glimpse-future-expressive-characters/)
- Cogley's α2.0.33 eye code already couples the lids to gaze. The top lids follow 80 % of the up/down range and the bottom lids 40 %. A trim pot rescales the lid limits. — [Cogley α2.0.33 Code/eyes.py (local)](../../inputs/reference/head_a2.0.33/Code/eyes.py)
- "Frame - Extras" adds a CheekBone band under the eyes. — [docs/PLAN.md](../../docs/PLAN.md)

### Inferences
- AU7 (squint) needs no new hardware: drive Cogley's BL and BR lower-lid servos up during a smile or a glare.
- AU6 (cheek raise) is a string pull per side, anchored to the skin over the cheekbone and pulled up and back toward the temple. Most of the visible fold comes from the skin bunching against the lower lid and the nasolabial line, so the anchor should sit low on the cheek. One MG90S can pull both cheeks through a split cable, as Eva does, at the cost of asymmetric expressions. Use two for a one-sided smirk, which suits Frankenstein.
- AU9 (nose wrinkle) and AU10 (sneer) share anatomy. The wolf-head roller arm shows one servo can give a sniff and then a snarl by travel alone, so one actuator per side could serve AU9/AU10 if the anchor sits at the side of the nose.

### Gaps
- No measured pull force or travel for a cheek raise on a 2–4 mm silicone skin was found.

## 3. Brows: one servo per brow vs two, inner and outer, furrow (AU4), linkage vs cable vs slider

### Takeaway
Two servos per brow (inner and outer) is the convergent choice in 2024–2026 hobby and research heads. It is the minimum that separates AU1 (inner raise, worry or sadness) from AU2 (outer raise) and gives AU4 (lowered, angry) and asymmetric brows. Cogley's design, now adopted, does exactly this with a flexible TPU bar bent between the two servos. A true furrow needs the inner ends to move toward the midline as well as down, which his bars do only as far as the bar geometry allows.

### Cited Findings
- Cogley's α2.0.33 brows: 4 servos (LO, LI, RI, RO), ±20° around centre, with poses for up, down, angry and happy. Angry = outer up and inner down; the opposite = worried. — [Cogley α2.0.33 Code/Brows.py (local)](../../inputs/reference/head_a2.0.33/Code/Brows.py); [docs/PLAN.md](../../docs/PLAN.md)
- Each brow bar prints in TPU so it bends when its two servos differ. PLA would be stiff, load the servos and crack at the pleats. — [docs/PLAN.md](../../docs/PLAN.md)
- The NUS/Moratuwa receptionist head (2026) has 4 brow DoF, 2 per brow for the inner and outer sections. — [arXiv 2607.17042](https://arxiv.org/html/2607.17042)
- The BAAI/Tsinghua head (2026) moves the brow ridge and the brow centre vertically with a spatial six-bar linkage. — [arXiv 2607.11688](https://arxiv.org/html/2607.11688)
- On the A-Lab android, a second eyebrow actuator ("eyebrow shrink") appears to help separate AU1 from AU2, which were more strongly coupled on the original head. — [arXiv 2412.13641](https://arxiv.org/html/2412.13641v1)
- Eva drives AU1, AU2, AU4 and AU5 with Bowden wires from a servo bank at the top of the skull, each servo pulling the left and right sides together. — [HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)
- An earlier Cogley-eye-based head used a single MG90S per brow, mounted in the forehead (search summary). — [Adafruit 3D Printed Animatronic Robot Head](https://learn.adafruit.com/3d-printed-animatronic-robot-head?view=all)
- The SWS forum expects magnets to work for brows, but not for closely spaced lip anchors. — [SWS forum](https://forums.stanwinstonschool.com/discussion/5676/attaching-control-cables-to-silicone-mask)
- The project's own concept study noted that one servo per brow gives one DoF, with the inner-versus-outer split fixed by the mechanism's path (D5). — [docs/PLAN.md](../../docs/PLAN.md)

### Inferences
- Keep Cogley's 4-servo brows. A Frankenstein glower lives mostly in AU4, with brows down and drawn together. His bars bend in the vertical plane, so check on the bench whether the inner ends also come toward the midline. If they do not, a small inward-angled cable or slot at the inner end would add the "drawn together" component without another servo.
- The procerus/corrugator crease between the brows (vertical frown lines) comes from skin bunching, so the skin thickness there and a soft anchor matter as much as the mechanism.

### Gaps
- No source measured the force a two-servo TPU brow needs against silicone. The PLAN's M2 exit test (travel and pull under a silicone sample) is still the way to get it.

## 4. Eyes and lids: EyeMech capabilities, lid independence, eye construction, and whether MG90S is fast enough for saccades and blinks

### Takeaway
EyeMech ε3.x has 6 servos: eye left-right, eye up-down, and an independent upper and lower lid per eye. That covers winks, squints, lid-follows-gaze and asymmetric lids, which is more than most hobby eyes offer. Its gaps are no vergence (both eyes share LR) and no independent eye roll. An MG90S closes a lid in roughly 95–120 ms with no load, at or just above the human closing phase of about 75–100 ms, so blinks will be near real speed but not crisp. Saccades are closer to human: the servo's no-load rating (about 600°/s) exceeds the peak velocity of small human saccades. For a lifelike look the eyeball matters as much as the motion: a painted iris under a clear, high resin or acrylic dome, gloss for the wet look, and a slightly translucent sclera.

### Cited Findings
**EyeMech**
- The EyeMech ε3.1 assembly has 38 solids and 6 servos (modelled as SG90). Its eyeballs measure 32.0 × 20.0 × 32.0 mm and sit at x = ±37.5 mm, a 75.0 mm eye spacing. The overall unit is 145.4 × 132.3 × 62.8 mm. — [inputs/reference/README.md](../../inputs/reference/README.md)
- α2.0.33 eye code: LR (40–140°) and UD (60–140°) are shared by both eyes. Each lid has its own servo: TL, BL, TR and BR, ranging 60–70° each (for example TL 90–160 and BL 90–30). — [Cogley Code/eyes.py (local)](../../inputs/reference/head_a2.0.33/Code/eyes.py)
- ε3.2 (posted 9 March 2025) lists six micro servos, SG90 or MG90s. The SG90 is described as cheaper but weaker and slower, and the MG90s as a middle ground (search summary of the design page). — [MakerWorld EyeMech listing](https://makerworld.com/models/1217039)
- An older design uses 4 MG90S to pitch, yaw and roll the eyes (search summary). — [Adafruit](https://learn.adafruit.com/3d-printed-animatronic-robot-head?view=all)
- Eva uses one servo to tilt both eyes vertically, a separate servo per eye horizontally (about ±45°), and an independent servo per lid (about 70° range). — [HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)
- The BAAI/Tsinghua head uses 4 eyelid linkages (upper and lower for both eyes) and 2 rotational DoF per eyeball. — [arXiv 2607.11688](https://arxiv.org/html/2607.11688)
- The NUS receptionist gives each eyeball pitch and yaw, but uses only two servos for the lids, with the upper and lower lids driven together. — [arXiv 2607.17042](https://arxiv.org/html/2607.17042)
- Garner Holt's Lincoln head uses 4 actuators per eye. — [MiceChat](https://micechat.com/168204-blurring-mechanical-line-ghps-new-animatronic-head-offers-glimpse-future-expressive-characters/)
- Columbia's Emo puts a camera in each pupil for eye contact. — [Columbia Engineering, 2024](https://engineering.columbia.edu/news/robot-can-you-say-cheese)

**Human speed targets**
- Blink: about 100–150 ms on average, up to about 400 ms. The down phase is about twice as fast as the up phase, roughly 75–100 ms. Another source gives a closing phase of 50–130 ms. A voluntary blink measured 572 ± 25 ms (search summary). — [Wikipedia: Blinking](https://en.wikipedia.org/wiki/Blinking); [Frontiers in Systems Neuroscience 2023](https://www.frontiersin.org/journals/systems-neuroscience/articles/10.3389/fnsys.2023.1242654/pdf); [Soma Technology](https://www.somatechnology.com/blog/thursday-thoughts/fast-average-blink)
- Saccade peak velocity: 15° saccades peak at 300–350°/s, 35° saccades at 475–525°/s, and the largest reach up to about 700°/s. Peak velocity plateaus above about 20° (search summary). — [Wikipedia: Saccade](https://en.wikipedia.org/wiki/Saccade); [EyeWiki: Saccade](https://eyewiki.org/Saccade)
- On the iCub, slow but variable robot eye movements were rated relatively more human-like, and human-range timing was most engaging for joint attention (search summary). — [Ghiglino et al., Paladyn 2020](https://www.degruyterbrill.com/document/doi/10.1515/pjbr-2020-0004/html?lang=en)

**Servo speed for lids and eyes**
- MG90S (TowerPro): 0.10 s/60° at 4.8 V and 0.08 s/60° at 6.0 V. — [TowerPro MG90S](https://www.towerpro.com.tw/product/mg90s-3/)

**Eye construction**
- Pour clear casting resin over painted irises for depth, then pour more resin into a silicone mold with the eyeballs in place for a "wet" finish, and sand and polish (search summary). — [Hackster.io, realistic printed eyes](https://www.hackster.io/news/these-animatronic-eyes-are-disturbingly-realistic-and-can-be-3d-printed-8f157393fda4)
- Ocularists paint the iris flat on the globe and dome clear acrylic over it. The dome should be high, close to a full half-sphere, for magnification (search summary). — [SWS forum, human eye prop](https://forums.stanwinstonschool.com/discussion/comment/15175)
- Print eyeballs at 0.2 mm layers or finer. ABS is slightly translucent and gives subsurface scattering. Airbrush the iris ring to fade out. Do not use cyanoacrylate on acrylic: it is too runny and hazes it (search summary). — [Instructables: Ultra Realistic Eyes](https://www.instructables.com/How-to-Make-Ultra-Realistic-Eyes-Using-3D-Printing)

### Inferences
- Lid timing: Cogley's lid servos travel 60–70°. With no load, an MG90S needs about 0.70 × 100 ms = 117 ms at 4.8 V and about 93 ms at 6 V. The project's 5.30 V rail sits in between, at about 105–110 ms. Real blinks close in 75–100 ms, so blinks will read slightly slow. Silicone on the lid makes it slower. Ways to speed it up: shorten the lid servo travel with a longer horn (trading torque), raise the servo rail toward 6 V (MG90S is rated 4.8–6 V), or keep lid skin very thin near the lash line. The KST X08 is no faster at 6 V (0.15 s/60°) and only reaches 0.09 s/60° at 8.4 V.
- Saccades: about 600°/s at the servo (0.10 s/60°) beats a 15° human saccade's 300–350°/s peak. Eye saccades should therefore look right if the motion is sent as a single jump with no easing. A cheap analog servo's acceleration and overshoot will set the real limit; nobody has measured that for EyeMech.
- Lid-follows-gaze is already in Cogley's code, and it is one of the strongest "alive" cues. Keep it when writing the new firmware.
- Eye size: EyeMech's eyeballs are 32 mm across, about a third larger than a human eye (about 24 mm, a common anatomy figure not sourced in this round). On a life-size Frankenstein head the visible iris diameter matters more than the globe. A 11–12 mm iris under a high dome keeps the eye reading as human size.

### Gaps
- No measured MG90S lid-blink time under silicone load was found. A slow-motion phone video of one lid would settle it.
- No source quantifies how much vergence (eyes converging on a near viewer) adds to perceived life at conversation distance.

## 5. Neck: pitch, yaw and roll for a life-size head; Stewart platforms vs gimbals; how much head motion matters

### Takeaway
Head motion is a strong life cue. The most natural pattern is eyes first, then the head following on a slower, eased curve. A life-size head with silicone weighs well over 1 kg, which rules out micro servos on a direct neck. Hobby builds use stacked MG996R-class or giant servos with a thrust bearing for yaw, or a spring-assisted parallel mechanism. Eva's MG90S Stewart platform stalled until springs carried the head. For this project the head is bolted to a fixed pedestal (D25), so adding a neck would be a structural redesign, not a bolt-on. The cheapest worthwhile step is yaw only, plus a little nod.

### Cited Findings
- Eva's neck is a modified Stewart platform of 6 MG90S. The standard version stalled under the head's weight, so springs were added to carry most of the load. Range is about 30° vertical and 45° horizontal. — [HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)
- The BAAI/Tsinghua head uses three NEMA 17 steppers: a parallel mechanism for nod and tilt, plus a yaw rotation. — [arXiv 2607.11688](https://arxiv.org/html/2607.11688)
- The NUS receptionist neck has 2 DoF, nod and turn. — [arXiv 2607.17042](https://arxiv.org/html/2607.17042)
- A 3-axis skull mod for a 12 ft skeleton uses 3 × Hitec HS-805BB giant servos (yaw, roll, pitch) and a thrust bearing (search summary). — [Hackaday.io project 181103](https://hackaday.io/project/181103-3-axis-skull-mod-for-12ft-skeleton/discussion-191300)
- A droid head uses 3 × MG996R, one per joint (search summary). — [Stardance devlog](https://stardance.hackclub.com/projects/2074/devlogs/232)
- One stacked design puts the yaw servo on the torso and the pitch servo on its output. It recommends a bearing for heads over 2 kg, so the pitch servo only balances the head while the bearing takes lateral loads. Ranges: pitch ±45°, roll ±30° (search summary). — [Salvius neck spec](https://salvius.org/spec/v01/neck/)
- Peeqo uses six modified RC servos in a Gough-Stewart base, with wires through the open centre. Another builder used six servos for pitch and roll only and noted that skipping yaw simplifies the maths (search summary). — [Hackaday, Peeqo](https://hackaday.com/tag/peeqo/); [Hackster.io, Stewart neck](https://www.hackster.io/news/a-stewart-platform-makes-the-perfect-neck-for-a-humanoid-robot-cd75cfb25764)
- Cogley built a humanoid neck from six miniature linear actuators arranged like neck muscles (search summary; article returned 403). — [Hackster.io](https://www.hackster.io/news/a-stewart-platform-makes-the-perfect-neck-for-a-humanoid-robot-cd75cfb25764)
- Cogley's Coglet companion bot has neck roll, neck pitch and base yaw. — [Hackster.io, Coglet](https://www.hackster.io/news/will-cogley-s-coglet-is-a-3d-printable-expressive-twin-camera-companion-bot-5cc02a04b718)
- Cogley's camera robot moves the eyes first, then turns the head, to imitate human behaviour (search summary). — [Hackster.io, A Head-Turning Robotics Project](https://www.hackster.io/news/a-head-turning-robotics-project-e86c97ac9d38)
- The Eddie head-and-neck robot, with a musculoskeletal neck, was rated significantly more natural and, by trend, more lifelike than a conventional robotic neck. There was no difference in humanlikeness, consciousness or elegance (search summary). — [Paladyn 2020 / DOAJ](https://doaj.org/article/37ed95b2c2e14cea9e0e598a24d1e109)
- In unintentional gaze shifts the head tends to follow the eyes (search summary of a Japanese robot-head study). — [Saitama University repository](https://sucra.repo.nii.ac.jp/records/13803)
- Cogley's α2.0 assembly has no neck. The project's plan is a fixed printed spine from the pedestal into his frame's nape ribs. — [docs/PLAN.md](../../docs/PLAN.md), Q17 / D25
- MG996R (TowerPro): 9.4 kg·cm at 4.8 V and 11 kg·cm at 6.0 V; 0.19 s/60° at 4.8 V (the table also lists 0.17) and 0.15 s/60° at 6 V; 55 g; 1400 mA stall. — [TowerPro MG996R](https://www.towerpro.com.tw/product/mg996r/)

### Inferences
- Priority order for a fixed-pedestal head: (1) yaw ±30–45° on a lazy-susan or thrust bearing, driven by an MG996R-class servo through a printed gear or belt, so the servo carries no weight; (2) a small nod about a pivot near the head's centre of mass, with a spring or counterweight carrying most of the moment, as Eva learned; (3) roll (head tilt) last. Most of the "curious" read comes from tilt, but it costs the most.
- A Stewart platform gives all three axes but needs six servos, inverse kinematics and springs, and its centre is crowded where the project's cable and fan-air path runs (D25). A stacked yaw-on-bearing plus pitch gimbal is simpler for one hobbyist and needs no drilling if the bearing seat is printed.
- Any neck changes the enclosure: the clamp ring and the pedestal (D26–D28) assume a fixed head.

### Gaps
- Head mass with skin is not measured yet, and it sets the neck servo size.
- No study quantifies how much yaw alone versus full 3-axis motion adds to perceived life.

## 6. Drive methods: direct linkage, push-pull rods, Bowden cables, strings and tendons; remote servo placement; backlash and friction

### Takeaway
Use rigid linkages where precision and push-pull matter (jaw, lips, eyes, lids), and Bowden cables or tendons where space is short and the motion is a pull against the skin's own elasticity (cheeks, nose, sneer, brows on some designs). Bowden cables let servos sit in a bank at the crown or on the jaw, but they add friction at every bend and backlash from sheath compression. Keep runs short and bends gentle, anchor both housing ends rigidly, and pre-tension against a return spring or the skin.

### Cited Findings
- Eva transmits all 12 mask motions with steel wires in Teflon Bowden tubes, from two servo banks (top of skull, and on the jaw) to cloth-strip anchors glued inside the mask. Each servo drives a symmetric left/right pair. The rigid skull face stops the pulls from collapsing the mask inward. — [HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)
- Morpheus combines rigid linkages (precise but hard to fit) with strings (compact but hard to control). — [arXiv 2507.16645](https://arxiv.org/abs/2507.16645)
- In a cable-driven wrist build, the sheath is in compression when the cable is in tension, so it buckles and rubs (search summary). — [Hackaday, 3-DOF wrist](https://hackaday.com/2022/11/03/3-dof-robot-arm-wrist-without-the-motor-weight)
- Friction at Bowden bends is the main drawback, and routing over pulleys significantly reduced it (search summary). — [University of Ljubljana repository](https://repozitorij.uni-lj.si/IzpisGradiva.php?id=119456)
- Backlash in Bowden transmissions is considerable. One fix is a tension-regulating mechanism. Friction and backlash depend on sheath curvature, which changes during motion (search summary). — [Sant'Anna repository](https://iris.santannapisa.it/handle/11382/532273)
- Bowden friction and compliance have been characterised experimentally (search summary). — [UT Austin repository](https://tdl-ir.tdl.org/handle/2152/31966)
- Creature-FX builders use brass guide tubes for lip-lift cables and RC aeroplane cables for smile pulls. — [SWS wolf head](https://forums.stanwinstonschool.com/discussion/comment/7448); [SWS smile/frown](https://forums.stanwinstonschool.com/discussion/11383/smile-frown-mechanism-for-canid-wolf-anthro-heads)
- Cogley's 2020 lips used guitar wire to reach servos placed further back (search summary). — [Planet Arduino](http://www.planetarduino.org/?cat=1871)
- Straight linkages matter: even metal gears wear quickly when fighting a bent rod or misaligned hinge (vendor blog). — [KPower](https://www.kpower.com/insight_servo/799.html)

### Inferences
- A Bowden pull only pulls. Every cable function needs a return: the skin's elasticity, a spring, or a second cable. Each cable also needs a little pre-tension to take up slack in the housing, or the first few degrees of servo travel do nothing.
- Practical hobby kit, none of which needs a drill: PTFE tube (2 mm ID, sold for 3D printers) as housing, 0.5–0.8 mm stainless or nylon-coated steel leader wire as the inner, printed clamps or ferrules at both ends, and crimp sleeves or a soldered loop at the anchor. Cut brass tube with a tube cutter, not a drill. Soldering suits the project: no drilling.
- Remote placement: putting AU6, AU9 and AU10 servos in a bank behind the face (Eva's top bank, or on the jaw for lower-face pulls) keeps the cheek area free of servos under Cogley's shell. Keep each run under about 150 mm with no bend tighter than about 25 mm radius (rule of thumb, not sourced) so friction stays small against an MG90S's few newtons.

### Gaps
- No measured friction loss for a PTFE-in-printed-channel Bowden at hobby scale was found.

## 7. Actuators: MG90S limits vs alternatives; noise; force needed to pull silicone; servo count, controllers and power

### Takeaway
The MG90S is adequate in torque for most face functions on a soft silicone skin (about 18 N at a 10 mm horn, stalled), and fast. Its real weaknesses are noise, idle buzz, gear wear, inconsistent clones (some "metal gear" units have a plastic first-stage pinion), and no position feedback. A drop-in PWM upgrade for noise is a coreless micro servo such as the KST X08 (coreless motor, steel gears, 8 mm thick), though it is no faster at 6 V. Serial-bus servos (Feetech SCS0009/STS3032, Dynamixel XL330) give feedback, compliance and quieter holding, but cost more and need a different bus and board. Linear micro actuators and SMA are too slow for speech. Pneumatics suit pros, not this build. The current Pico PWM approach scales to 16 channels per RP2040 (24 on an RP2350), so adding 2–4 servos fits the existing boards.

### Cited Findings
**MG90S (baseline)**
- TowerPro: 13.4 g; 22.8 × 12.2 × 28.5 mm; stall torque 1.8 kg·cm at 4.8 V and 2.2 kg·cm at 6.6 V; 0.10 s/60° at 4.8 V and 0.08 s/60° at 6.0 V; dead band 1 µs; aluminium 6061-T6 gears; 0–55 °C. — [TowerPro MG90S](https://www.towerpro.com.tw/product/mg90s-3/)
- AZ-Delivery datasheet: 1.8 kgf·cm at 4.8 V and 2.2 kgf·cm at 6 V; 0.1 s/60° at 4.8 V and 0.08 s/60° at 6 V; stall current 700 mA. — [AZ-Delivery MG90S datasheet](https://cdn.shopify.com/s/files/1/1509/1638/files/MG90S_Micro_Servo_Datenblatt_AZ-Delivery_Vertriebs_GmbH.pdf)
- Tinytronics: stall current 750 mA ±10 % at 4.8 V and 860 mA ±10 % at 6 V. — [Tinytronics MG90S datasheet](https://www.tinytronics.nl/product_files/000263_Data_Sheet_of_MG90S_Analog_Servo_Motor.pdf)
- Dead band varies by seller: 5 µs is the most common figure, others list 1 µs or 10 µs. The "MG90S" name covers different products (search summary). — [Components101](https://components101.com/motors/mg90s-metal-gear-servo-motor)
- Buyer's teardown guide: "metal gear" does not guarantee all-metal. Some clones use a plastic first-stage pinion that slips and strips on the smooth motor shaft under vibration. Open one on arrival and return it if that gear is plastic. — [TuyaOpen forum MG90S buying guide](https://forum-tuyaopen.discourse.group/t/mg90s/24)
- Eva's lessons with 25 MG90S: servo noise was significant and distracting, and quieter servos were recommended. Overheating limited the longest continuous run to 3 hours in a cool room. Jaw opening was much smaller than expected because the 2 mm Ecoflex 00-30 mask resisted stretching; suggested fixes were stronger servos, a thinner mask or more jaw weight. — [HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)

**Alternatives (exact specs where found)**
- **KST X08 V6.0** (PWM, 2023 sheet): 3.8–8.4 V (rated 7.4 V); 1.40 kgf·cm at 3.8 V, 2.20 at 6.0 V and 2.80 at 8.4 V; 0.18 s/60° at 3.8 V, 0.15 at 6.0 V and 0.09 at 8.4 V; coreless DC motor; hardened steel gears; aluminium case; 23.5 × 8 × 16.8 mm; 8 g; 333 Hz; 900–2100 µs; default travel ±60° (120°); programmable soft start. — [KST X08 V6.0 technical specification](https://cdn.shopify.com/s/files/1/0570/1766/3541/files/X08_V6.0_Technical_Specifcation.pdf)
- **KST X08 Plus**: about 3.85 kg·cm at 6.0 V and 5.30 kg·cm at 8.4 V; 9 g; digital (search summary). — [servodatabase.com](https://servodatabase.com/servo/kst/x08-plus)
- **EMAX ES08MA II** (analog, metal gear, about 12 g, 23 × 11.5 × 24 mm): 0.12 s/60° at 4.8 V and 0.10 at 6 V. Torque figures conflict across retailers: 1.6/2.0, 1.5/1.8 or 1.8/2.2 kg·cm at 4.8/6 V (search summary). — [Little Bird](https://littlebirdelectronics.com.au/products/emax-es08ma-ii-12g-mini-metal-gear-analog-servo-for-rc-model); [servodatabase.com](https://servodatabase.com/servo/emax/es08ma)
- **Feetech SCS0009** (TTL serial bus, daisy-chained): 4–7.4 V; stall 2.3 kg·cm; rated 0.75 kg·cm; 1:416 metal gearbox; 10-bit (1024-step) position; 23.2 × 12.1 × 25.25 mm (MG90S-sized); €13.85 (sold out at the time). No speed figure was found. — [OpenELAB](https://openelab.io/a/s/products/seeed-studio-feetech-scs0009-ultra)
- **Feetech STS3032**: 4.8–6 V; peak stall 4.5 kg·cm and rated 1.5 kg·cm at 6 V; 0.09 s/60° at 6 V; magnetic encoder; 38.4 kbps–1 Mbps; feedback for load, position, speed, voltage and temperature. A 7.4 V variant also exists (search summary). — [rcdrone.top](https://rcdrone.top/products/feetech-sts3032-servo-motor)
- **Dynamixel XL330-M288-T**: 18 g; 20 × 34 × 26 mm; 288.4:1; stall 0.42/0.52/0.60 N·m at 3.7/5.0/6.0 V; stall current 1.11/1.47/1.74 A; no-load 76/103/123 rpm; 3.7–6.0 V (5 V recommended); 12-bit contactless absolute encoder; current-based position control (sets a torque limit); TTL half-duplex multidrop, 3.3 V logic, 5 V tolerant, up to 4 Mbps; plastic case and gears; cored motor. No price found. — [ROBOTIS e-Manual](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/)
- **Actuonix PQ12-R** micro linear servo (RC PWM, 6 V): 20 mm stroke; 30:1 = 28 mm/s no load (peak power 15 N at 15 mm/s); 63:1 = 15 mm/s (30 N at 8 mm/s); 100:1 = 10 mm/s (40 N at 6 mm/s, 50 N max lifted); 22 g; US$88–150 depending on retailer. — [Actuonix PQ12 datasheet](https://cdn.robotshop.com/media/f/fir/rb-fir-42/pdf/actuonix-pq12-datasheet.pdf); [SparkFun](https://www.sparkfun.com/actuonix-pq12-100-6-r-micro-actuator.html); [RobotShop](https://www.robotshop.com/products/actuonix-pq12-r-linear-actuator-20mm-301-6v-rc-control)
- **Shape-memory alloy** (Flexinol 0.006 in): about 330 g pull, about 400 mA, about 1 s to contract, 1.2–2.0 s to cool. Stroke is typically 2–5 % of wire length (search summary). — [Dynalloy/Flexinol technical data](https://cdn.robotshop.com/media/d/dyn/rb-dyn-01/pdf/flexinol-technical-data.pdf); [Images Scientific](https://www.imagesco.com/nitinol/wire.html)
- **Pneumatics**: the A-Lab android uses 14 pneumatic actuators. Garner Holt's earlier Yeti head used linear pneumatics, but its later Lincoln head is electric servo, made "turnkey" with no compressed air. — [arXiv 2412.13641](https://arxiv.org/html/2412.13641v1); [MiceChat](https://micechat.com/168204-blurring-mechanical-line-ghps-new-animatronic-head-offers-glimpse-future-expressive-characters/)
- Research heads in 2026 still use cheap 9 g servos: BAAI/Tsinghua uses "GuoHua 9g digital micro servos" (180°), driven through cascaded PCA9685s over I²C at 30 Hz. — [arXiv 2607.11688](https://arxiv.org/html/2607.11688)
- InMoov's i2 head build list uses 15 JX PDI-1109MG servos and advises against cheap SG90s (search summary of inmoov.fr). — [InMoov](https://inmoov.fr/?p=17227)

**Noise**
- Coreless motors have no iron core, so they vibrate less and run quieter (vendor claim). One vendor test measured a budget "quiet" servo at 36 dBA. Silicone grease quiets gears at some loss of power. More gear reduction means more noise (forum). — [KPower](https://www.kpower.com/insight_servo/6718.html); [Arduino forum](https://forum.arduino.cc/t/quitening-the-servo-motors/27030)
- Idle hum is the servo fighting to hold position. Stopping the pulses when no motion is needed silences it, but the servo may then drift under load. — [Arduino forum](https://forum.arduino.cc/t/quitening-the-servo-motors/27030)
- The Evil Mad Scientist coreless replacement motor for SG90-class servos is sold as reducing noise significantly (vendor claim). — [RobotShop](https://uk.robotshop.com/products/evil-mad-scientist-coreless-replacement-servo-motor-axidraw)

**Skin force**
- Hanson says Frubber needs about 1/10 of the force to elongate, and about 1/13 to compress, compared with an equivalent solid elastomer. That lets smaller motors be packed more densely; Han has about 40 motors and K-Bot had 24. These are Hanson's own claims, mostly from 2007. — [Design News, 2007](https://www.designnews.com/robotics/humanoid-robots-put-best-faces-forward)
- Adding porosity to a platinum silicone lowers the force needed to deform a face skin (Virginia Tech thesis, search summary). — [VTechWorks](https://vtechworks.lib.vt.edu/items/512a04bc-60e4-47d1-91cb-c04a25a4a59f)
- Ecoflex 00-50 needs about 3 × the actuation pressure of Ecoflex 00-30 for the same bending (soft-actuator study, search summary). — [Sant'Anna repository](https://iris.sssup.it/handle/11382/492375)
- The project's own estimate for keyed lids: each 2A rivet head holds about 1 N through its neck, and peel at the lash edge is the weak mode. — [docs/PLAN.md](../../docs/PLAN.md), Q22

**Controllers and power**
- RP2040: 8 PWM slices × 2 outputs = 16 hardware PWM channels; any GPIO can carry PWM. RP2350: 12 slices = 24 channels. Both outputs of a slice share a frequency (fine for 50 Hz servos). — [RP2040 datasheet §4.5](https://xiao-seeed-rp2040-renode.readthedocs.io/en/latest/specification/rp2040-datasheet/06_chapter_4_peripherals/05_4.5_pwm/); [RP2350 PWM notes](https://ugandapico.pages.dev/core-concepts/pwm/pwm-in-rp2350)
- Cogley's mouth board drives its 12 servos straight from Pico GPIO 4–15 in MicroPython, with no PCA9685. — [Cogley Code/Mouth.py (local)](../../inputs/reference/head_a2.0.33/Code/Mouth.py)
- The Waveshare Pico Servo Driver gives 16 channels at 16-bit resolution, takes 6–12 V in and supplies up to 3 A from its onboard 5 V regulator. — [Welectron](https://welectron.com/Waveshare-19767-Pico-Servo-Driver)

### Inferences
- **Force budget**: MG90S stall is 1.8 kgf·cm = 0.177 N·m. That gives about 17.7 N at a 10 mm horn, 11.8 N at 15 mm and 8.8 N at 20 mm. Keep working loads below about a third of stall for life and quiet (rule of thumb): about 6 N at 10 mm. Tip speed at 600°/s on a 10 mm horn is about 105 mm/s, enough for 5–10 mm lip moves in 50–100 ms. Eva's small jaw opening shows the real limit is skin stiffness at large strains, not servo torque at small ones. The jaw (2 × MG996R) is the function to watch with FX-Pro.
- **Dragon Skin FX-Pro vs Ecoflex 00-30**: FX-Pro is generally listed as Shore 2A, stiffer than Ecoflex 00-30 (not verified in this round; check Smooth-On's TDS). Thinning the skin over the corners, lips and cheeks (2–3 mm) and adding Slacker there is the cheapest way to cut actuator load.
- **Best upgrade path, cheapest first**: (1) genuine MG90S with all-metal first stage (check on arrival); (2) stop PWM pulses on idle channels in firmware to kill hum (a one-line change); (3) KST X08 V6.0 (coreless, steel gears) for the noisiest or most visible channels, such as lids and eyes, running at 6–7.4 V on a separate rail for speed; (4) serial-bus servos only for a v2, because they need a half-duplex UART bus (a buffer chip or Feetech's adapter, some soldering) and a firmware rewrite.
- **Not recommended here**: PQ12-class linear actuators (20 mm takes 0.7–2 s, much too slow for speech; maybe a slow nostril flare); SMA (1 s on, 1–2 s off, and a 10 mm stroke needs about 250 mm of wire); pneumatics (compressor noise, plumbing and valves, against the project's no-air, fixed-enclosure plan).
- **Power**: worst-case all-stall draw for 17 × MG90S plus 2 × MG996R is about 17 × 0.86 + 2 × 1.4 = 17.4 A at 6 V, under the project's 20 A buck. Real simultaneous peaks are far lower. Adding 4 more MG90S adds about 3.4 A worst case.
- **Channel count**: the mouth Pico uses 12 of 16 channels, so 4 PWM-capable outputs remain for AU10 and AU6 pulls per side. A Pico 2 (RP2350) adds 8 more.

### Gaps
- No independent dB measurements of MG90S vs KST X08 vs Feetech were found.
- No current KST X08 or XL330 retail price was confirmed.
- No measured force (in N) to move a mouth corner or cheek on a 2–4 mm platinum silicone face skin was found. The project should measure it with a luggage scale on an FX-Pro coupon, as PLAN M2/M4 already planned.
- SCS0009 speed was not found.

## 8. Builder case studies and lessons

### Takeaway
The open, well-documented builds (Eva, Cogley, InMoov, the 2026 RSS and AIM heads) agree on: a rigid underskull matching the skin's inner surface; magnets or snaps at many points rather than glue; 9 g servos in large numbers (12–25); two servos per brow; separate upper and lower lids; and multi-DoF mouth corners. The recurring regrets: servo noise, skin stiffness limiting the jaw, skull and skin shapes that do not match (the skin caves in or twists), overheating on long runs, and necks underestimated for head weight. Exaggeration helps avoid the uncanny valley.

### Cited Findings
- **Eva (Columbia, HardwareX 2020)**: 25 MG90S (mask 12, neck 6, eyes 5, jaw 2), about US$900 total (servos about $90), 2.25 kg of PLA/ABS. Lessons: jaw limited by mask stiffness; servo noise; 3 h thermal limit; Stewart neck stalled without springs; early skull and mask shapes did not match and the mask caved in (fixed with a shared face profile); latex and TangoBlack+ too rigid, so silicone; surprise and fear hard to tell apart. — [HardwareX 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256)
- A student replication of Eva found some printed parts did not match and needed manual modification (search summary). — [ShanghaiTech report](https://robotics.shanghaitech.edu.cn/sites/default/data/2025-04/moma2023project-eva-face.pdf)
- **Emo (Columbia, Science Robotics 2024)**: 26 actuators, silicone skin on a magnetic attachment system, a camera in each pupil, and a self-model that anticipates a smile by about 840 ms. — [Columbia Engineering](https://engineering.columbia.edu/news/robot-can-you-say-cheese); [Popular Science](https://www.popsci.com/technology/emo-smile-robot-head/)
- **Will Cogley's silicone head (2024)**: 14 servos (brow raise, lip sync, tongue); skin held by magnets in clamp pieces, leaving the rest free to flex; Arduino Mega with a custom shield. Exaggerated movements and proportions push it toward cartoonish to dodge the uncanny valley, though it still reads as somewhat too human. Skin casting caused waste and curing problems. — [Arduino Blog](https://blog.arduino.cc/2024/12/09/this-frighteningly-realistic-animatronic-head-features-expressive-silicone-skin/); [Circuit Digest](https://circuitdigest.com/news/fully-3d-printed-animatronic-head-with-lifelike-silicone-skin-built-by-youtuber-will-cogley)
- **Cogley α2.0.33** (the head this project is building): mouth 12 channels, eyes 6, brows 4 (local code); MicroPython on Picos; two boards (mouth; eyes, brows and neck). — [local Code/](../../inputs/reference/head_a2.0.33/Code/Mouth.py); [inputs/reference/README.md](../../inputs/reference/README.md)
- **InMoov i2 (Gael Langevin, Make Vol. 93, July 2025)**: more than 17 servos, 13 in the face (eyes X/Y, lids, brows, cheeks, upper lip, two forehead servos), plus a neck on three pistons. Thin silicone skin from a printed two-part mold, held by Velcro on most parts, glued at the eyelids, magnets in places. The skin makes it harder to build; LLM-composed expressions are sometimes incoherent (a smile with disgust). — [Make: Skin Deep](https://makezine.com/article/technology/robotics/skin-deep-evolving-inmoovs-facial-expressions-with-ai)
- **BAAI/Tsinghua (RSS 2026)**: 21 face DoF on 9 g digital servos, a PLA skeleton, magnetic skin, PCA9685 at 30 Hz and 3 NEMA 17 steppers for the neck. 3D printing and skin took about 42 h. Their automatic mechanism synthesis succeeded on 10 of 15 face shapes. A compact head took 22.8 h to design by hand vs 11.7 min automatically. — [arXiv 2607.11688](https://arxiv.org/html/2607.11688)
- **NUS/Moratuwa receptionist (AIM 2026)**: 22 servos for 21 DoF. Skin modified from the Eva mold, held by snap fasteners at deformation points and magnets at rigid areas. "Fear" was the weakest expression at 70.0 % recognition. — [arXiv 2607.17042](https://arxiv.org/html/2607.17042)
- **Garner Holt Lincoln (2017, pro)**: 45 actuators (12 lips, 4 per eye), "dozens of unique flexible magnetic grippers" holding the skin, swapped in under 2 minutes without tools, and a 1000 fps control system vs about 32 fps typical. — [MiceChat](https://micechat.com/168204-blurring-mechanical-line-ghps-new-animatronic-head-offers-glimpse-future-expressive-characters/)
- **Ameca (Engineered Arts)**: 27 actuators in head and neck (vendor listing). A later upgrade added 12 facial actuators. Per-region counts and actuator type were not found. — [Robozaps](https://www.robozaps.com/products/ameca); [Nerdist](https://nerdist.com/article/robot-gets-more-realistic-expressions-engineering-arts-ameca)
- **Wolf head (SWS forum)**: the builder credits Rick Lazzarini's "Organic Mechanics" and designs for maintenance; an open-cell foam head degraded after about 8 years of use. — [SWS forum](https://forums.stanwinstonschool.com/discussion/comment/7448)
- An android study found only surprise and happiness were classified correctly from its expressions (search summary). — [PMC8019968](https://pmc.ncbi.nlm.nih.gov/articles/PMC8019968/table/T2)

### Inferences
- For this project the most "alive per servo" additions, in order: (1) AU10 sneer/snarl, one MG90S per side on Bowden cables, using the mouth Pico's spare channels; (2) AU6 cheek raise per side, with the lower lids lifting in firmware for a Duchenne smile and squint; (3) yaw on a bearing if the enclosure can take it. Stop idle PWM and replace lid and eye servos with quieter coreless units if noise distracts.
- The skin-attachment pattern the project already chose (snap pads at moving points, fixed points on the shell and cheek bone) matches the 2026 NUS design and Garner Holt's practice. The Eva lesson says the inner shape of the skin must match the shell, or it caves or twists under the pulls.

### Gaps
- No 2025–2026 hobby head with clearly better expression than Cogley's α2 was found, and no Hackaday 2025–2026 feature came up in searches.
- What builders "wish they had done differently" is documented mainly by Eva; Cogley's own retrospective was not found in public text.
