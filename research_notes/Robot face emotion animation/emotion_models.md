# Psychological and computational models of emotion for a continuous, dynamic robot face (Frank)

Scope note for the report writer: primary texts read in full this session were Gebhard 2005 (ALMA), Becker-Asano and Wachsmuth 2010 (WASABI), the WASABI v0.7.1 manual, Mehrabian 1996 (Big Five in PAD terms), Marsella and Gratch 2009 (EMA), and a reproduction of the Russell and Mehrabian 1977 22-emotion PAD table. Kismet, Probo, Boukricha, D'Mello, Rozin and Cohen and the Geneva Emotion Wheel come from abstracts, project pages and search summaries; their numbers are marked as such. Anything known only from background knowledge is in the Gaps sections, not the findings.

## 1. Dimensional models (circumplex, PAD, Kismet's arousal-valence-stance) and where Frank's ten tags sit

### Takeaway
PAD (pleasure, arousal, dominance, each -1..+1) is the best-documented continuous space with published coordinates for emotion words, and both ALMA and WASABI run on it. Published coordinates exist for surprised, excited, annoyed/irritated, concentrated (WASABI puts it at the origin) and several neighbours. I found none for curious, skeptical, confused or vulnerable. The cognitive states sit close together near the origin, so PAD alone cannot tell them apart on a face.

### Cited Findings
- Russell and Mehrabian (1977) PAD values, as reproduced in Table 4 of a 2021 paper (scale -1..+1, order P, A, D): afraid -0.64, 0.60, -0.43; angry -0.51, 0.59, 0.25; annoyed -0.28, 0.17, 0.04; anxious 0.01, 0.59, -0.15; ashamed -0.57, 0.01, -0.34; caring 0.64, 0.35, 0.24; content 0.86, 0.20, 0.62; disgusted -0.60, 0.35, 0.11; embarrassed -0.46, 0.54, -0.24; excited 0.62, 0.75, 0.38; furious -0.44, 0.72, 0.32; grateful 0.64, 0.16, -0.21; guilty -0.57, 0.28, -0.34; hopeful 0.51, 0.23, 0.14; impressed 0.41, 0.30, -0.32; joyful 0.76, 0.48, 0.35; lonely -0.66, -0.43, -0.32; proud 0.77, 0.38, 0.65; sad -0.64, -0.27, -0.33; surprised 0.40, 0.67, -0.13; terrified -0.62, 0.82, -0.43 — [Kim et al. 2021, arXiv 2104.10117, Table 4](https://arxiv.org/pdf/2104.10117). Caution: I extracted the text from a two-column PDF. Two values look odd (anxious P = +0.01; a "devastated" row with P = +0.14 that I left out), so check them against the 1977 original before use.
- The original 1977 norms are semantic-differential ratings of 151 emotion terms by 300 respondents (Journal of Research in Personality, "Evidence for a three-factor theory of emotions"). Most later papers reproduce only the 22-term subset — [search summary citing the 1977 paper](https://www.researchgate.net/publication/222741832_Evidence_for_a_Three-Factor_Theory_of_Emotions); [arXiv 2104.10117](https://arxiv.org/pdf/2104.10117).
- ALMA reuses the Russell-Mehrabian values where they exist (its Anger is -0.51, 0.59, 0.25, the same as R&M "angry"; its Fear is -0.64, 0.60, -0.43, the same as "afraid") and fills the missing OCC emotions "by exploiting similarities to comparable emotion types" — [Gebhard 2005, ALMA, Table 2 and text](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).
- ALMA's full OCC-to-PAD table (P, A, D; mood octant): Admiration 0.5, 0.3, -0.2 (Dependent); Anger -0.51, 0.59, 0.25 (Hostile); Disliking -0.4, 0.2, 0.1 (Hostile); Disappointment -0.3, 0.1, -0.4 (Anxious); Distress -0.4, -0.2, -0.5 (Bored); Fear -0.64, 0.60, -0.43 (Anxious); FearsConfirmed -0.5, -0.3, -0.7 (Bored); Gloating 0.3, -0.3, -0.1 (Docile); Gratification 0.6, 0.5, 0.4 (Exuberant); Gratitude 0.4, 0.2, -0.3 (Dependent); HappyFor 0.4, 0.2, 0.2 (Exuberant); Hate -0.6, 0.6, 0.3 (Hostile); Hope 0.2, 0.2, -0.1 (Dependent); Joy 0.4, 0.2, 0.1 (Exuberant); Liking 0.40, 0.16, -0.24 (Dependent); Love 0.3, 0.1, 0.2 (Exuberant); Pity -0.4, -0.2, -0.5 (Bored); Pride 0.4, 0.3, 0.3 (Exuberant); Relief 0.2, -0.3, 0.4 (Relaxed); Remorse -0.3, 0.1, -0.6 (Anxious); Reproach -0.3, -0.1, 0.4 (Disdainful); Resentment -0.2, -0.3, -0.2 (Bored); Satisfaction 0.3, -0.2, 0.4 (Relaxed); Shame -0.3, 0.1, -0.6 (Anxious) — [Gebhard 2005, Table 2](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).
- ALMA names the eight PAD octants: +P+A+D Exuberant, +P+A-D Dependent, +P-A+D Relaxed, +P-A-D Docile, -P-A-D Bored, -P-A+D Disdainful, -P+A-D Anxious, -P+A+D Hostile — [Gebhard 2005, Table 1](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).
- WASABI's primary emotions in PAD (scale ±100) with base intensity: Angry (80, 80, 100) 0.75; Annoyed (-50, 0, 100) 0.75; Bored (0, -80, 100) 0.75; **Concentrated (0, 0, ±100) 0.75**, described as a "non-emotional state" shown with a neutral face; Depressed (0, -80, -100) 0.75; Fearful (-80, 80, 100) 0.25; Happy (80, 80, ±100) and (50, 0, ±100) 0.75; Sad (-50, 0, -100) 0.75; Surprised (10, 80, ±100) 0.0. The coordinates are "derived from some of the values given in Russell and Mehrabian", but the authors moved "bored" on purpose, away from the R&M location. Happy is placed four times so that it covers the whole positive-pleasure region — [Becker-Asano and Wachsmuth 2010, Table 1 and Sect. 3.1](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).
- Note the fearful anomaly: WASABI codes Fearful at D = +100 in Table 1. Yet in the text, fears-confirmed "can only be perceived by the agent, when he feels submissive as in the case of fearful", which contradicts the table — [WASABI 2010](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf). This may be an extraction or typesetting error; check it against the original.
- Kismet's affect space has three axes, arousal, valence and stance. Each active releaser is tagged with arousal, valence and stance markers during appraisal; for example fear is high arousal, negative valence, closed stance — [MIT Sociable Machines, emotions page](https://groups.csail.mit.edu/lbr/sociable/emotions.html); [Breazeal 2003, IJHCS 59:119-155](https://faculty.cc.gatech.edu/~athomaz/papers/Breazeal-ijhcs03.pdf).
- Course slides describe Kismet's valence as how desirable a stimulus is and stance as how approachable it is, and give a value range of [-1250, 1250] per axis. I did not verify this against the paper — [Chernova, CS7633 Lecture 11 slides](https://faculty.cc.gatech.edu/~chernova/CS7633/slides/Lecture11.pdf).
- Sony's AIBO model (Arkin et al.) is similar but uses confidence as its third axis instead of stance — [search summary of Breazeal-related sources](https://typeset.io/pdf/emotion-and-sociable-humanoid-robots-2inax9grw9.pdf).
- Probo places its basic facial expressions as vectors in a 2D emotion space based on Russell's circumplex (valence, arousal) — [Saldien et al. 2010, IJSR, via typeset](https://typeset.io/pdf/expressing-emotions-with-the-social-robot-probo-26xsv3ejcs.pdf); [Saldien et al. 2008, design of Probo](https://rua.ua.es/dspace/handle/10045/12583).
- Cognitive states as affect: D'Mello and Graesser's model of affect during deep learning centres on confusion, engagement/flow, frustration and boredom. Confusion comes from impasses: if the impasse is resolved, the learner moves back to engagement; if confusion persists, it slides into frustration and then boredom. Time-series analyses at roughly 110 points per tutoring session confirmed confusion-engagement, boredom-frustration and confusion-frustration oscillations — [D'Mello and Graesser 2012, Learning and Instruction 22(2):145-157](https://mail.editlib.org/p/110193); [CU record](https://vivo.colorado.edu/display/pubid_164504).
- Rozin and Cohen (2003) found that confusion, "think-concentrate" and worry were among the most frequently reported expressions in naturally occurring faces. Confusion was the most common descriptor for asymmetric expressions, is "characterized principally by facial movements around the eyes" and has many properties usually attributed to emotions. A commentary argued that the observation method exaggerated how common these expressions are — [Rozin and Cohen 2003, Emotion, via scilit](https://scilit.com/publications/c731c444dab2c5e917bfb788672f4962).

### Inferences
- Frank's resting character ("dry, skeptical, mildly unimpressed") falls in ALMA's **Disdainful** octant (-P, -A, +D). ALMA's Reproach (-0.3, -0.1, 0.4) is the published emotion closest to "skeptical". A default mood of about (-0.15, -0.15, +0.35) would be "slightly disdainful" in ALMA terms.
- Proposed PAD anchors for the ten tags. Only those marked "published" have direct sources; the rest are my interpolations from the cited neighbours:
  - neutral: (0, 0, 0)
  - surprised: (0.40, 0.67, -0.13), published (R&M "surprised")
  - excited: (0.62, 0.75, 0.38), published (R&M "excited")
  - irritated: (-0.28, 0.17, 0.04), published (R&M "annoyed")
  - concentrating: (0, 0, ±) in WASABI, published but uninformative
  - curious: about (0.3, 0.4, 0.0), between R&M "impressed" (0.41, 0.30, -0.32) and "hopeful" (0.51, 0.23, 0.14)
  - amused (dry): about (0.45, 0.25, 0.35), a weaker "joyful" (0.76, 0.48, 0.35) with high D
  - skeptical: about (-0.25, 0.1, 0.45), near ALMA Reproach / Disliking
  - confused: about (-0.2, 0.35, -0.25), negative-leaning and aroused, low control, near R&M "embarrassed" but milder
  - vulnerable: about (-0.3, 0.1, -0.55), near ALMA Shame / Remorse (-0.3, 0.1, -0.6)
- Dominance does the work of separating Frank's states: skeptical and amused are high D, while confused and vulnerable are low D. Kismet's "stance" (approach vs withdraw) is the closest robot analogue to D and fits curious (open/approach) vs skeptical (closed) well.
- Concentrating, neutral and, partly, curious and skeptical all sit within about 0.4 of the origin. PAD-nearest-neighbour expression selection will flicker between them. The engine therefore needs either a fourth "epistemic" axis (for example certainty or attention) or a categorical overlay that carries the tag's own face. Rozin and Cohen's data (confusion and concentration are common and are mostly eye and brow movements) supports treating these as first-class expressions, not as low-intensity emotions.

### Gaps
- No published PAD coordinates were found for "curious", "skeptical", "confused", "concentrating" (other than WASABI's origin placement) or "vulnerable". The full 151-term R&M 1977 list might include "puzzled", "interested", "bored" or "skeptical", but I could not retrieve it. The original paper (J. Res. Personality 11:273-294, Table 4 or appendix) needs a library copy.
- Russell (1980) circumplex angles (for example the published angular positions of the 28 affect words) were not retrieved this session. From background knowledge, unverified here: valence is horizontal, arousal vertical, and the words lie roughly on a circle.
- Pekrun's epistemic-emotion work (surprise, curiosity, enjoyment, confusion, anxiety, frustration, boredom) would give valence and arousal classifications for curiosity and confusion, but I did not retrieve it.

## 2. Categorical models and wheels (Ekman, Plutchik, Geneva Emotion Wheel): intensity and mixing

### Takeaway
Categorical models give recognisable prototypes but handle intensity and mixing only coarsely. The Geneva Emotion Wheel adds an explicit intensity radius and allows blends, laid out on valence × control (power), which is close to PAD's P and D. None of these models covers Frank's cognitive tags.

### Cited Findings
- Geneva Emotion Wheel: emotion families are arranged in a circle on two dimensions, valence and control (also called control/power), which form four quadrants (negative/low control, negative/high control, positive/low control, positive/high control). Intensity is rated by distance from the hub and by circle size. Respondents can pick a single family or a blend of several. The current version has 20 families; the 2005 prototype (v1.0) had 16 terms. Positions come from GRID data, and the authors advise against relabelling or moving families — [Geneva Emotion Wheel, Swiss Center for Affective Sciences](https://www.unige.ch/cisa/gew); [Aalto summary](https://experience.aalto.fi/geneva-emotion-wheel/). The original source is Scherer 2005, Social Science Information 44(4):693-727.
- Plutchik-style composition: a 2021 representation-learning paper, "inspired by Plutchik (1980) which proposed the eight" primary emotions, derived dyads such as Excited = Anticipating + Joyful, Lonely = Sad + Afraid, Grateful = Trusting + Joyful, Sentimentality = Trust + Sadness. It also derived proportional mixes, for example "Annoyed can be composed of 90% Angry and 10% Anticipating" — [arXiv 2104.10117](https://arxiv.org/pdf/2104.10117).
- Ekman's basic-emotion prototypes in FACS form: happiness 6+12; sadness 1+4+15; surprise 1+2+5B+26; fear 1+2+4+5+7+20+26; anger 4+5+7+23; disgust 9+15+17; contempt R12A+R14A — [Facial Action Coding System, Wikipedia](https://en.wikipedia.org/wiki/Facial_Action_Coding_System).
- WASABI solves Ekman's single-positive-emotion problem ("in case of high Pleasure Ekman's set of basic emotions only contains one obviously positive emotion, namely happiness") by placing Happy in PAD space four times. It also adds non-Ekman states (bored, annoyed, depressed, concentrated) — [WASABI 2010, Sect. 3.1](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).

### Inferences
- The GEW's control axis is the same idea as PAD dominance and Kismet stance. All three independent lines of work keep a third "power/approach" dimension, which supports keeping D in Frank's engine.
- For Frank, a GEW-like representation (tag = family, intensity = radius, several families active at once) maps directly onto "a weight per expression basis". It is the simplest categorical scheme that still supports blends.
- Ekman's set covers only surprised, irritated (a mild form of anger), amused (a form of happiness) and, at a stretch, skeptical (contempt-like, unilateral). Curious, concentrating, confused and vulnerable fall outside it.

### Gaps
- Plutchik's intensity rings (for example annoyance → anger → rage; interest → anticipation → vigilance) and his primary, secondary and tertiary dyad tables were not retrieved from a primary source this session. They are background knowledge only.
- The full list of the 20 GEW families was not confirmed. From background knowledge, it includes interest and contempt but no explicit "confusion".

## 3. FACS action units for the ten expressions and how robots map AUs to actuators

### Takeaway
FACS gives a clean intermediate layer: each AU has a muscle, an A-E intensity scale and L/R/unilateral codes, and published AU sets exist for surprise, amusement/happiness, anger/irritation and contempt. For confusion the AUs are AU4 + AU7, although studies differ. For concentration the evidence is mostly brow lowering. For skepticism, the commonly cited unilateral AU2 has no primary source I could find.

### Cited Findings
- AU names and muscles: AU1 inner brow raiser (frontalis, medial); AU2 outer brow raiser (frontalis, lateral); AU4 brow lowerer (corrugator, depressor supercilii/glabellae); AU5 upper lid raiser (levator palpebrae); AU6 cheek raiser (orbicularis oculi, orbital); AU7 lid tightener (orbicularis oculi, palpebral); AU9 nose wrinkler; AU10 upper lip raiser; AU12 lip corner puller (zygomaticus major); AU14 dimpler (buccinator); AU15 lip corner depressor; AU17 chin raiser; AU20 lip stretcher; AU23 lip tightener; AU24 lip pressor; AU25 lips part; AU26 jaw drop; AU27 mouth stretch; AU28 lip suck; AU43 eyes closed; AU45 blink; AU46 wink; AU61-64 eyes left/right/up/down — [FACS, Wikipedia](https://en.wikipedia.org/wiki/Facial_Action_Coding_System).
- Intensity letters: A trace, B slight, C marked/pronounced, D severe/extreme, E maximum. Asymmetry codes: R (right), L (left), U (unilateral, side unspecified), and a trailing A for "bilateral but has a stronger side". Contempt R12A+R14A is the canonical published unilateral prototype — [FACS, Wikipedia](https://en.wikipedia.org/wiki/Facial_Action_Coding_System).
- Confusion: in tutoring studies, brow lowering (AU4) and eyelid tightening (AU7) correlated with confusion, while inner and outer brow raising (AU1, AU2) correlated with frustration — [Grafsgaard et al., automatically recognizing facial expression, via typeset](https://typeset.io/pdf/automatically-recognizing-facial-expression-predicting-1nb7yjn8a5.pdf). The underlying method had two independent judges FACS-code learners' faces (McDaniel, D'Mello et al. 2007), and the features separated confusion, delight and frustration — [CogSci proceedings, escholarship](https://escholarship.org/content/qt9w00945d/qt9w00945d.pdf).
- AU sets for confusion vary across studies: a 2018 review table lists confusion as AU4+AU7 in one study and AU1, AU4, AU7, AU12 or AU45, AU1, AU4 in others — [Smart Learning Environments 2018, Table 1](https://slejournal.springeropen.com/articles/10.1186/s40561-018-0080-z/tables/1).
- Confusion is "characterized principally by facial movements around the eyes" and is the most common label for asymmetric expressions — [Rozin and Cohen 2003](https://scilit.com/publications/c731c444dab2c5e917bfb788672f4962).
- Concentration: congenitally blind and sighted adults showed similar eyebrow movements during concentration, sadness and anger — [Bar-Ilan University record, 2009 study](https://cris.biu.ac.il/en/publications/facial-expressions-in-various-emotional-states-in-congenitally-bl/).
- PAD-to-AU mapping for a virtual face: Boukricha, Wachsmuth, Hofstätter and Grammer (ACII 2009, pp. 119-125) built a control architecture that sets facial expressions from PAD values. It uses a face repertoire built from an empirical rating study; the virtual human Emma has 44 FACS AUs, and the repertoire is about 6000 faces arranged in PAD space for two dominance values (dominant, submissive). The same data was later used for the reverse direction (AUs → PAD) for facial mimicry — [Boukricha et al. 2009, Bielefeld record](https://pub.uni-bielefeld.de/record/1998773); [Towards facial mimicry for a virtual human](https://pub.uni-bielefeld.de/record/1991242).
- Kismet maps affect space to motors with nine prototype (basis) postures. Each one influences most facial features to some degree; for example the valence prototypes act most strongly on lip curvature but also move the ears, eyelids, brows and jaw — [MIT Sociable Machines, facial expression page](https://groups.csail.mit.edu/lbr/sociable/facial-expression.html).
- Probo maps an emotion vector in 2D valence-arousal space onto its degrees of freedom through an emotional interface — [Saldien et al. 2008](https://rua.ua.es/dspace/handle/10045/12583); [Saldien et al. 2010](https://typeset.io/pdf/expressing-emotions-with-the-social-robot-probo-26xsv3ejcs.pdf).

### Inferences
Proposed AU targets for Frank's tags, mapped onto his servos. The tags with direct FACS prototypes are surprised, amused and irritated; the cognitive tags come from the confusion and concentration evidence above.
- **surprised**: AU1+2+5B+26 (published). Inner and outer brow up on both sides, upper lids wide, jaw drop.
- **amused**: AU6+12 (published happiness). Corner servos up; AU6 has no actuator, so imply it by lowering the lower lids slightly. For "dry" amusement, use an asymmetric smile (U12) at low intensity.
- **irritated**: anger subset AU4+7(+23). Brow inner ends down, lids tightened (lids part-closed), lips pressed (lip servos).
- **skeptical**: unilateral outer brow raise (U2) and/or unilateral AU4 on the other side, plus contempt-like R12A+R14A (one corner up). Asymmetry is the key cue; FACS supports L/R coding.
- **confused**: AU4+AU7, mostly eyes and brows, ideally asymmetric (per Rozin and Cohen), with a small head-tilt equivalent through the eyes (gaze offset).
- **concentrating**: AU4 (light) with lids slightly lowered; gaze fixed or averted (AU61-64 hold); lips pressed (AU24).
- **curious**: AU1+2 at low-mid intensity, AU5 slight, gaze toward the target, a small jaw opening (AU25).
- **excited**: AU1+2+5 + 6+12 + 25/26.
- **vulnerable**: sadness brow AU1+4 (inner ends up and together), lid lowering, AU15 slight (corners down), gaze down (AU64).
- **neutral**: no AUs, with Frank's mood bias layered on top (see section 5).

The four brow servos (inner and outer per side) can produce AU1, AU2 and AU4 independently and unilaterally, which covers most of the discriminating cues for the cognitive tags. The mouth-corner servos stand in for the AU12 vs AU15 axis, the lids for AU5 vs AU7/43, and the jaw for AU25/26/27.

### Gaps
- No primary FACS source was found for skepticism or disbelief (the unilateral AU2 "eyebrow raise" is folk knowledge). No published AU prototype was found for curiosity, interest or vulnerability.
- Kismet's DOF count and the coordinates of its nine basis postures were not given on the pages reached. From background knowledge, unverified: Kismet has 15 facial DOF.
- Boukricha's regression or lookup details (how PAD selects AU intensities) were not retrieved; only abstracts were available.

## 4. Appraisal theory (OCC, Scherer's CPM, EMA): useful when an LLM already picks the emotion?

### Takeaway
Appraisal theory mainly answers "which emotion, how strong". Frank's LLM already answers the first part, so a full OCC or CPM engine is redundant. The useful parts are the appraisal variables (expectedness, desirability, control) as intensity and dominance modifiers, and EMA's idea of mood biasing emotion intensity.

### Cited Findings
- ALMA's emotion generation is OCC-based (an EmotionEngine with 24 emotion types, combined with the five-factor personality model). Personality traits control emotion intensities, and appraisal rules are hand-written in AffectML (for example GoodEvent desirability = 0.7; BadActOther praiseworthiness = -0.3) — [Gebhard 2005](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf); [ALMA project site: 24 emotion types, 8 mood types, 5 personality types](https://alma.dfki.de/).
- EMA (Marsella and Gratch 2009) is built on Smith and Lazarus's appraisal theory. It tries to explain both fast, reflex-like responses and slow, deliberative ones by re-running the same appraisal on a changing causal interpretation. It maps appraisal patterns to labels (for example Expectedness(self, p) = low → Surprise) — [Marsella and Gratch 2009, Cognitive Systems Research](https://www.cs.uky.edu/~sgware/reading/papers/marsella2009ema.pdf); [EMA abstract](https://www.khoury.northeastern.edu/~marsella/publications/abstracts/MarsellaCSR09-abstract.html).
- EMA's mood: the intensities of all appraisal frames with the same label are summed and passed through a sigmoid to [0, 1], giving a mood vector over emotion labels. Mood "bleeds over" into appraisal: a frame of label L with intensity X gets the mood-adjusted intensity X + Mood(L). The frame that drives coping is "the most recently accessed appraisal frame with the highest mood-adjusted intensity" — [Marsella and Gratch 2009](https://www.cs.uky.edu/~sgware/reading/papers/marsella2009ema.pdf).
- WASABI separates cognition (a BDI agent, which triggers emotions and sets dominance from the situation) from embodiment (continuous PAD dynamics), and treats the OCC prospect-based emotions (hope, fears-confirmed, relief) as cognitively triggered "secondary" emotions — [WASABI 2010](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).
- Gebhard admits a limitation of ALMA: "an emotion's intensity is not influenced by the current mood", although people in a bad mood tend to perceive events negatively — [Gebhard 2005, Sect. 6](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).

### Inferences
- Treat the LLM as the appraisal module (WASABI's "cognition"). Have it emit the tag plus, optionally, two or three appraisal-style scalars (intensity 0-1, expectedness, a "who is in control" flag). That gives what OCC or CPM would compute without building them.
- Use EMA-style mood congruence: `effective_intensity = clamp(tag_intensity + k * mood_affinity(tag))`. Then Frank's disdainful baseline makes skeptical and irritated come easily and excited take more to trigger, which matches "theatrical only when genuinely fascinated".

### Gaps
- Scherer's component process model (stimulus evaluation checks for novelty, intrinsic pleasantness, goal conduciveness, coping potential and norm compatibility, with predicted AU sequences per check) was not retrieved this session. Its predicted AU-per-check timing could help with onset choreography (for example AU1+2 for novelty first, then AU4 for goal obstruction). Background knowledge only.
- The OCC (Ortony, Clore and Collins 1988) original structure (22 types, intensity variables) was not retrieved directly; ALMA's 24-type list stands in for it.

## 5. Computational affect architectures with dynamics (ALMA, WASABI, Kismet, EMA, FAtiMA): equations, constants, mood pull

### Takeaway
ALMA and WASABI both publish implementable dynamics. ALMA: PAD emotion points with linear decay, a "virtual emotion centre" that pulls and pushes mood, mood returning to a personality-derived default, updated every 500 ms. WASABI: a discrete spring-mass system on emotional valence (x) and mood (y), a boredom axis (z), projected to PAD, with distance-based emotion "awareness". Both run easily at 25-50 Hz in Python.

### Cited Findings
**ALMA (Gebhard 2005)**
- Three layers: emotions (short-term, event-bound, decay), moods (medium-term) and personality (long-term, Big Five) — [Gebhard 2005](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).
- Default mood from Big Five (O, C, E, A, N in -1..1): **P = 0.21·E + 0.59·A + 0.19·N; A = 0.15·O + 0.30·A − 0.57·N; D = 0.25·O + 0.17·C + 0.60·E − 0.32·A**. Worked example: O 0.4, C 0.8, E 0.6, A 0.3, N 0.4 → (0.38, -0.08, 0.50), "slightly relaxed". I checked the arithmetic and it holds — [Gebhard 2005](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).
- Mood strength is the norm of the PAD vector. ALMA says the longest distance in an octant is 3 and splits it into thirds: slightly, moderate, fully. Example: (0.25, -0.18, 0.12) = slightly relaxed — [Gebhard 2005](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf). (The Euclidean corner distance is √3 ≈ 1.73; "3" matches an L1 norm. The paper is inconsistent here.)
- Mood update ("pull and push"): the virtual emotion centre (VEC) is the centroid in PAD of all active emotions, and its intensity is the average of their intensities (max 1.0). If the current mood lies between the origin and the VEC, it is pulled toward the VEC; if it lies at or beyond the VEC, it is pushed further out into its current octant. With no active emotions, mood is not pushed. The VEC "jumps" between octants quickly, so it drives mood only slowly — [Gebhard 2005, Sect. 3, Fig. 2](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).
- Timing constants: "usual mood change time" (octant centre to octant centre) is 10 minutes. Mood returns to the default mood over 20 minutes for the longest distance. The example config has `EmotionDecay time="20000" period="500" function="linear"`, `EmotionBaseline threshold="0.4"`, `MoodReturn time="600000" period="500"`, and the text gives "decayed over a certain amount of time (for example, 1 minute)". Affect is recomputed every 500 ms — [Gebhard 2005, Fig. 3 and Sect. 4](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf). Internal inconsistency: the config's MoodReturn of 600 000 ms is 10 min, but the text says the return time is 20 min.
- Evaluation: a user study found the generated emotions and moods rated as plausible — [ALMA site](https://alma.dfki.de/); [Gebhard and Kipp 2006, "Are computer-generated emotions and moods plausible to humans?"](https://www.springerprofessional.de/are-computer-generated-emotions-and-moods-plausible-to-humans/1232988).

**Mehrabian 1996 (source of ALMA's personality mapping)**
- Mehrabian regressed each Big Five factor on trait P, A, D (standardised). Extraversion = .24P + .72D (the OCR gives .12D in the table copy; check it); Agreeableness = .76P + .17A − .19D; Conscientiousness = .29P + .28D; **Emotional stability = .?0P − .55A** (first digit illegible in the scan; replications give .37P − .44A and .43P − .4?A; corrected for attenuation .57P − .65A); Sophistication (openness) = … + .28A + .60D. Multiple R = .83, .76, .46, .73, .39 for the five equations. After correcting for attenuation, PAD accounted for 81%, 69%, 25%, 72% and 42% of the variance in extraversion, agreeableness, conscientiousness, emotional stability and sophistication — [Mehrabian 1996, Australian Journal of Psychology 48:86-92](https://www.cs.uky.edu/~sgware/reading/papers/mehrabian1996analysis.pdf).
- Mehrabian's Eysenck neuroticism = -.26P + .49A − .25D. Emotional stability is "almost equal degrees of pleasant and unarousable characteristics" — [Mehrabian 1996](https://www.cs.uky.edu/~sgware/reading/papers/mehrabian1996analysis.pdf).

**WASABI (Becker-Asano and Wachsmuth 2010; Becker, Kopp and Wachsmuth 2004)**
- Emotional impulses (valence) displace emotional valence x. Mood y is a separate bipolar valence that x drives, and it is regulated back to neutral "much slower" than x. Dominance comes from the cognition's view of the situation (for example MAX feels dominant on his own turn, submissive otherwise). The architecture was implemented in the agent MAX — [WASABI 2010, Sects. 3, 3.3, 4.2](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf); [Becker, Kopp and Wachsmuth 2004, ADS LNAI 3068](https://link.springer.com/content/pdf/10.1007/978-3-540-24842-2_15).
- Update equations (WASABI v0.7.1 manual), per axis: **F(t) = −d·x(t−1); a(t) = F(t)/m; v(t) = a(t)·Δt + v(t−1); s(t) = v(t)·Δt + s(t−1)**, with separate spring constants dx (emotion) and dy (mood), a "slope" setting how fast mood follows emotional valence, a mass m for the reference point, and an internal update rate in Hz set independently of the network message rate. GUI test impulses are ±50 (on the ±100 scale). PAD projection: **P = (x + y)/2, A = |x|**, D set independently — [WASABI manual](https://becker-asano.de/index.php/research/wasabi/78-wasabi-manual?start=3). The manual gives no default values for d, m, slope or rate.
- Boredom: with no impulses, z increases linearly (range -1 to 0 in a lecture summary), and arousal becomes A = |x| + z, i.e. PAD = ((x+y)/2, |x| + z, d) — [Hoey, CS886 lecture 6 slides](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/lecture6.pdf); [2004 paper record: emotion axis, orthogonal mood axis, later a boredom axis](https://pub.uni-bielefeld.de/record/1607115). The manual's worked example uses A = |x| without z, so the versions differ.
- Emotion "awareness likelihood" from PAD distance (Eq. 1): **w_pe = (1 − (d_pe − Φ_pe)/(Δ_pe − Φ_pe)) · i_pe**, with Δ_pe > Φ_pe. Here d_pe is the distance from the current PAD point to the emotion's coordinate, Δ is the activation threshold (computation starts when d < Δ), Φ is the saturation threshold (w = base intensity i_pe when d < Φ), and i_pe is the base intensity. For emotions placed several times, the nearest copy is used — [WASABI 2010, Eq. 1](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf). The Greek symbol names were lost in text extraction; the roles are as stated in the paper.
- Constants used: in the primary-only condition, every primary emotion had saturation threshold 0.2, activation threshold 0.64 and base intensity 1.0. In the full condition, Table 1 base intensities were used, and Surprised had saturation threshold 0.3 and base intensity 0.0, so it shows only when cognition triggers it. Cognitive triggers temporarily set an emotion's base intensity to 1.0. Secondary emotions have a lifetime of 10.0 by default with linear decay. Secondary emotions are 4-vertex polygons in the D = ±100 planes with per-vertex intensities (Hope: (100,0)→0.6, (100,100)→1.0, (−100,100)→0.5, (−100,0)→0.1, on both D planes; Relief: (100,0)→1.0, (100,50)→1.0, (−100,50)→0.2, (−100,0)→0.2; Fears-confirmed only in the low-D plane), linearly interpolated — [WASABI 2010, Sects. 3.2-3.3, 4.2.1, Table 2](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).
- Worked behaviour: Fearful (base 0.25) is "slightly" active before any trigger when PAD drifts near it; the cognitive trigger makes it "very fearful"; within the next 10 s its intensity decreases and the reference point moves, so it falls back to "fearful" with no further input — [WASABI 2010, Sect. 4.1](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).
- Mood congruence comes from PAD proximity: a positive mood makes negative emotions less likely, citing Neumann et al. — [WASABI 2010, Sect. 3](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).

**Kismet (Breazeal 2003)**
- The affect state is a single point moving in (A, V, S) space; releasers tagged with A, V and S drive it, and the expression is interpolated in real time from nine basis postures — [MIT facial expression page](https://groups.csail.mit.edu/lbr/sociable/facial-expression.html); [MIT emotions page](https://groups.csail.mit.edu/lbr/sociable/emotions.html).

**EMA**: mood = per-label sigmoid of summed appraisal-frame intensities, added to new frames' intensities (see section 4) — [Marsella and Gratch 2009](https://www.cs.uky.edu/~sgware/reading/papers/marsella2009ema.pdf).

### Inferences
- **The ALMA neuroticism signs look flipped.** Mehrabian's emotional stability loads +P and −A, and neuroticism loads −P and +A. ALMA's printed +0.19·N (pleasure) and −0.57·N (arousal) match *emotional stability*, not neuroticism. Anyone using neuroticism as input should negate those two terms, or pass emotional stability = −N. ALMA's coefficients also do not appear verbatim in Mehrabian's regressions (which predict Big Five from PAD, not the reverse), so treat them as an engineering mapping, not a validated inversion.
- Frank's personality → default mood. With O high (0.6), C mid (0.3), E low-mid (0.0), A low (-0.4), emotional stability mid (0.3): P = 0.21·0 + 0.59·(-0.4) + 0.19·0.3 = -0.18; A = 0.15·0.6 + 0.30·(-0.4) − 0.57·0.3 = -0.20; D = 0.25·0.6 + 0.17·0.3 + 0.60·0 − 0.32·(-0.4) = +0.33, giving (-0.18, -0.20, +0.33), "slightly disdainful". This matches his brief, which supports ALMA-style personality biasing. (The trait values are my choice.)
- At 25-50 Hz, WASABI's Euler integration is stable for small Δt (0.02-0.04 s) as long as ω·Δt << 1. A pure spring (F = −d·x, as written in the manual) oscillates forever. For a face, add damping, ideally critical (c = 2√(d·m)), so that an emotion decays without overshooting past neutral; or deliberately under-damp it (ζ ≈ 0.6-0.8) for a small "rebound" after surprise. ALMA's 500 ms tick is too slow for servo output; run the affect state at the servo rate or interpolate between 2 Hz affect updates.
- ALMA's time constants (emotion decay 20-60 s, mood change 10 min, mood return 20 min) suit long sessions. For short visitor interactions, Frank probably needs a mood half-life of about 1-5 minutes and emotion decay of 2-10 s for display, while keeping the LLM-visible emotion longer. WASABI's "fearful decays within 10 s" is a published reference point for display decay.
- Map Frank's tags onto WASABI-style triggers. A tag sets that emotion's intensity to 1.0 × tag strength, with a lifetime and linear or exponential decay, and also injects a valence impulse into x (positive for curious, excited, amused; negative for irritated, confused, skeptical). The spring dynamics then generate mood drift and mood-congruent "leakage" (for example a mildly skeptical face emerging on its own when mood is negative and nothing is happening). Boredom (z) lowering arousal during silence gives idle behaviour for free.

### Gaps
- Default WASABI parameter values (d, m, slope, update rate, boredom rate) were not found; the manual says they are loaded from configuration files. The 2004 paper (which has the full dynamics, possibly including a damping term) was not reachable (Springer and CORE returned 403).
- Kismet's emotion-process equations (activation, decay or habituation constants, winner-take-all arbitration) were not retrieved; the Breazeal 2003 PDF returned 403.
- FAtiMA's decay function was not retrieved. From background knowledge only, unverified: FAtiMA uses exponential decay, intensity(t) = I0·e^(−b·t), with a per-emotion decay rate and threshold.

## 6. Intensity and blending: weighted bases, nearest neighbour in PAD, linear mixing, and pitfalls

### Takeaway
The published systems use three blending approaches. Kismet interpolates basis postures over a continuous space. WASABI computes a distance-based weight per discrete emotion, then shows those emotions' expressions. Boukricha uses an empirically rated face repertoire indexed by PAD. Linear AU or servo mixing is simple but can produce unintended third expressions, and antagonistic AUs cancel on shared actuators.

### Cited Findings
- Kismet: nine basis postures; the location in (A, V, S) space sets each prototype's relative contribution; "interpolation-based technique", running in real time; each prototype affects most facial features — [MIT facial expression page](https://groups.csail.mit.edu/lbr/sociable/facial-expression.html).
- WASABI: distance-based weights per emotion (Eq. 1 above), with activation and saturation thresholds giving a dead zone and a plateau. The seven facial expressions cover nine primary emotions (several emotions share a face, for example annoyed and depressed use the "sad" face) — [WASABI 2010, Table 1, Sect. 3.1](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).
- Boukricha: about 6000 rated faces arranged in PAD space for dominant and submissive values, from which PAD selects AU intensities — [Bielefeld record](https://pub.uni-bielefeld.de/record/1991242); [ACII 2009 record](https://pub.uni-bielefeld.de/record/1998773).
- The FACS prototypes overlap: fear = 1+2+4+5+7+20+26 contains the surprise brow (1+2) plus the anger brow (4), and sadness = 1+4+15 — [FACS, Wikipedia](https://en.wikipedia.org/wiki/Facial_Action_Coding_System).
- The Plutchik-style embedding work treats blends as proportional mixes (Annoyed ≈ 90% Angry + 10% Anticipating) — [arXiv 2104.10117](https://arxiv.org/pdf/2104.10117).

### Inferences
- **The third-expression pitfall, concretely for Frank's brow.** Blending curious (AU1+2, brows up) with irritated (AU4, brows down and together) linearly gives AU1+2+4 on the inner brow, which is the fear/worry brow in FACS. Blending vulnerable (AU1+4) with skeptical (U2) can read as distress. Mitigations: (a) blend in AU space with explicit "conflict" rules (AU1 and AU4 together only when intended); (b) give each tag ownership of facial regions (brow, lids, mouth) and blend per region, with the dominant tag winning a region outright above a weight threshold; (c) limit simultaneous active tags to two and crossfade them, not sum them.
- **Antagonist cancellation.** On a single servo, AU12 (corner up) and AU15 (corner down) are opposite signs of the same actuator, so 50/50 mixing yields neutral, and amused + vulnerable becomes an expressionless mouth. Use max-magnitude or priority selection per actuator, not a signed sum, when signs conflict.
- **Asymmetry must survive blending.** Skeptical and confused rely on L/R differences (FACS U/L/R codes; Rozin and Cohen's asymmetric confusion). Mixing a symmetric expression with an asymmetric one at equal weight halves the asymmetry. Keep a separate "asymmetry" channel (signed, per brow and corner) that is added after the symmetric blend.
- Recommended pipeline for 25-50 Hz:
  1. LLM tag + strength.
  2. Per-tag intensity envelopes (attack, hold, decay), plus the mood/PAD state.
  3. Per-tag AU/servo basis poses scaled by intensity, combined per region with conflict rules, plus a mood-derived low-amplitude bias pose (for example a slight disdainful brow and lid set).
  4. Asymmetry overlay.
  5. Per-servo rate and acceleration limiting and soft limits.
- Nearest-neighbour in PAD alone (snapping to the closest tag) is easy but jumps between faces when the state sits between anchors. WASABI's thresholded distance weights (dead zone Δ, plateau Φ) are a ready-made fix.

### Gaps
- I found no empirical study that measured how people perceive linearly blended robot expressions (for example the rate of unintended readings). This remains a design risk to test on the physical face.

## 7. Evidence on how well people recognise dimensional vs categorical robot expressions

### Takeaway
I found little directly comparable, retrievable evidence this session. Kismet and Probo report recognition studies, but I could not retrieve the numbers. The only hard numbers obtained are from WASABI (perceived maturity, not recognition) and from human cognitive-state expressions.

### Cited Findings
- WASABI study (n = 23 students, 11 vs 12 per condition): MAX with primary + secondary emotions was judged significantly older than with primary emotions only (27.5 ± 7.5 vs 19.8 ± 7.7 years; two-tailed t-test, unequal variances, p = 0.025), with no gender effect. Richer emotion dynamics change how "mature" the character seems — [WASABI 2010, Sect. 4.2](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).
- ALMA: generated emotions and moods were rated plausible in a user study — [Gebhard and Kipp 2006](https://www.springerprofessional.de/are-computer-generated-emotions-and-moods-plausible-to-humans/1232988); [ALMA site](https://alma.dfki.de/).
- Probo: Saldien et al. evaluated recognition of Probo's emotion-space expressions and compared it with similar robots — [Saldien et al. 2010](https://typeset.io/pdf/expressing-emotions-with-the-social-robot-probo-26xsv3ejcs.pdf) (numbers not retrieved).
- Kismet: Breazeal 2003 has a section evaluating the readability of Kismet's expressions (Section 8) — [search summary pointing to Breazeal 2003](https://typeset.io/pdf/recognition-of-affective-communicative-intent-in-robot-2paxo1nx8o.pdf) (numbers not retrieved).
- Human cognitive-state expressions are frequent and readable: naive observers labelled natural faces as confused, thinking or concentrating, and worried more often than most basic emotions — [Rozin and Cohen 2003](https://scilit.com/publications/c731c444dab2c5e917bfb788672f4962). Automated and FACS-coded studies separate confusion, frustration and delight by AU patterns — [escholarship](https://escholarship.org/content/qt9w00945d/qt9w00945d.pdf).

### Inferences
- Even dimensional robots (Kismet, Probo) present and evaluate their output as categorical prototypes at the anchor points. The continuous space is used for movement between anchors, not as the thing people are asked to recognise. That supports a hybrid design for Frank: recognisable per-tag poses at full intensity, with continuous interpolation and mood bias between them.
- Since the WASABI study shows that people notice the depth of emotion dynamics (perceived age), Frank's "mood under emotion" layer is likely to affect how sophisticated he seems, even when individual expressions are recognised equally well.

### Gaps
- Per-emotion recognition rates for Kismet (Breazeal 2003) and Probo (Saldien 2010) were not retrieved (the PDFs returned 403 or were empty). From background knowledge, unverified: Probo reported roughly 84% overall recognition.
- I found no study that directly compares recognition of dimensional (interpolated) and categorical (prototype) robot faces under matched conditions.
- Recognition data for cognitive-state expressions (confused, skeptical, concentrating) on robot faces was not found.

## 8. Assessment: which frameworks suit a Python engine at 25-50 Hz with ten LLM tags as input

### Takeaway
The best fit is a hybrid. Use PAD (ALMA's coordinates and personality-to-mood mapping, with the neuroticism signs fixed) as the continuous state for mood and dynamics. Use WASABI-style spring dynamics and thresholded distance weights for onset, decay and mood leakage. Render through per-tag FACS-style basis poses blended per facial region, Kismet-fashion, with an asymmetry channel. Full appraisal engines (OCC, CPM, EMA, FAtiMA) are unnecessary because the LLM plays the cognition role.

### Cited Findings
- WASABI already separates "cognition triggers emotion (base intensity → 1.0)" from "embodiment computes PAD dynamics", which matches LLM tags driving a face engine — [WASABI 2010](https://cs.uwaterloo.ca/~jhoey/teaching/cs886-affect/papers/WASABIAAMAS2010.pdf).
- WASABI's dynamics are four lines of explicit Euler per axis, with a configurable internal update rate — [WASABI manual](https://becker-asano.de/index.php/research/wasabi/78-wasabi-manual?start=3).
- ALMA gives PAD coordinates for 24 emotions, octant mood labels, a personality-to-default-mood formula and published time constants — [Gebhard 2005](https://cs.huji.ac.il/course/2005/aisemin/articles2006/docs/pa1a3_29.pdf).
- Kismet and Probo show that interpolating basis postures over a continuous space drives real motors in real time — [MIT](https://groups.csail.mit.edu/lbr/sociable/facial-expression.html); [Saldien 2008](https://rua.ua.es/dspace/handle/10045/12583).
- EMA's mood-adjusted intensity (X + Mood(label)) is a one-line mood-congruence rule — [Marsella and Gratch 2009](https://www.cs.uky.edu/~sgware/reading/papers/marsella2009ema.pdf).

### Inferences
Fit of each framework for Frank:
- **Russell circumplex (2D)**: good for arousal → speed and amplitude. It cannot separate skeptical from irritated or confused from vulnerable, because D is missing. Use it as a sub-space only.
- **PAD**: the best continuous state, with published numbers (R&M 1977, ALMA, WASABI) and personality mapping. The cognitive tags cluster near the origin, so it needs a categorical overlay.
- **Kismet A-V-S**: the stance axis fits Frank's approach (curious) vs closed (skeptical). Few published numbers. Its basis-posture interpolation is the right render idea.
- **Ekman / FACS**: the right render vocabulary (AU per servo group, A-E intensity, L/R codes). It covers only 3-4 of the ten tags as prototypes.
- **Plutchik / GEW**: GEW's "intensity = radius, blends allowed" model maps well onto per-tag weights. Neither gives dynamics.
- **OCC / CPM**: redundant for selection; at most a few appraisal scalars from the LLM.
- **ALMA**: good for mood and personality (default mood, pull/push, return). Its 500 ms tick and long time constants need tuning. Fix the neuroticism signs.
- **WASABI**: good for dynamics (spring-mass, boredom, distance-thresholded awareness). Add damping and pick constants empirically.
- **EMA**: good for its mood-congruence rule. The rest is a deliberative planner and out of scope.
- **FAtiMA**: not assessed (not retrieved).

Concrete engine sketch, each step citing its model of origin:
1. Personality → default mood P0 = (-0.18, -0.20, +0.33) (ALMA, sign-fixed).
2. Each LLM tag → (PAD anchor, basis pose, intensity, lifetime) (ALMA/WASABI tables plus the anchors in section 1).
3. Active-emotion list with attack and decay envelopes (ALMA linear decay; WASABI lifetime).
4. Valence impulse into a damped spring x, mood y following x slowly, boredom z rising in silence (WASABI).
5. Mood also pulled and pushed by the VEC and relaxing toward P0 (ALMA).
6. Displayed weights = tag envelopes plus WASABI Eq. 1 "leakage" from the PAD state near each anchor, with mood congruence (EMA).
7. Per-region blending of AU poses with conflict and asymmetry rules (Kismet/FACS), plus a mood bias pose.
8. Servo smoothing and limits.

The whole chain is a few hundred lines of Python and costs microseconds per 20-40 ms tick.

### Gaps
- None of the frameworks gives validated time constants for a talking-head performance (as opposed to a game or tutoring agent). Onset times (for example a surprise apex in about 100-300 ms) and decay times need either facial-dynamics literature (not covered here) or tuning on the real servos.
- No published evaluation was found of hybrid "PAD state + categorical render" designs against pure-dimensional or pure-categorical designs on a physical servo face.
