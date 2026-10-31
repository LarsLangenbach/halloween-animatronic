# Facial DOF priorities for a lifelike animatronic face, and how real robot faces budget their actuators

Research date 2026-10-30. Scope: physical degrees of freedom only (emotion models, FACS-to-emotion tables, software, blink/gaze timing and lip sync were covered in an earlier round). "Search summary" below marks a fact taken from a search-engine summary of the linked page rather than from a full read of it; treat those as one step less certain.

## 1. Which face regions and action units carry the most perceptual weight?

### Takeaway
Observers rely mainly on two regions, the eyes/brows and the mouth, and each emotion leans on one of them: sadness and fear on the eyes, happiness and disgust on the mouth, surprise on both. For a physical character, movement in the upper face (brows, lids, forehead) matters out of proportion to its actuator cost: a still upper face is a documented cause of uncanniness, especially for fear, surprise, sadness and disgust.

### Cited Findings
- Wegrzyn et al. (2017, PLOS ONE 12(5): e0177239) revealed faces tile by tile (6x8 grid) and computed each tile's diagnostic value. The most diagnostic tiles sat over FACS action-unit areas, and observers "were mostly relying on the eye and mouth regions". Expressions lay on a continuum from sadness and fear (eye-reliant) to disgust and happiness (mouth-reliant). — [Wegrzyn et al. 2017, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5426715)
- Eisenbarth & Alpers (2011), "Happy Mouth and Sad Eyes", eye tracking: anger and sadness are more recognisable from the eye region (frowning), happiness and disgust from the mouth (smiling), and fear and surprise depend on both regions (search summary of a secondary citation). — [Eisenbarth & Alpers 2011, ResearchGate](https://www.researchgate.net/publication/51587978_Happy_Mouth_and_Sad_Eyes_Scanning_Emotional_Facial_Expressions)
- Blais et al. (2012), Bubbles technique: the mouth is the most informative single region for telling expressions apart. Calder et al. (2000): the eye region alone suffices for anger and fear. Both are secondary citations surfaced by search; the originals were not opened, and other studies disagree on surprise (eyes, mouth or both). — [Frontiers in Neuroscience 2022 (secondary)](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2022.937939/full); [Frontiers in Psychology 2022 (secondary)](https://www.frontiersin.org/articles/10.3389/fpsyg.2022.966623/full)
- A 2025 eye-tracking study of basic expressions found that accurate recognition depends on integrating upper- and lower-face features, not on either region alone (search summary). — [Recognition and Misclassification Patterns, 2025, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12565503/)
- Dynamic expressions: fixations go selectively to the diagnostic regions of each expression in the KDEF-dyn dynamic face set (search result title and summary). — [Calvo et al., Scientific Reports 2018](https://www.nature.com/articles/s41598-018-35259-w)
- Upper face and the uncanny (Tinwell, Grimshaw, Abdel-Nabi & Williams, Computers in Human Behavior 2011; earlier conference versions 2010): characters lacking upper-face movement during speech were rated more uncanny. The effect was strongest for fear and surprise and was also present for sadness and disgust, but not for anger or happiness. Uncanniness was strongest for realistic, human-like male characters lacking movement of the eyelids, eyebrows and forehead. — [Tinwell et al., AAU repository PDF](https://vbn.aau.dk/ws/files/63140615/Facial_expression_of_emotion_and_perception.pdf)
- Tinwell, quoted in Times Higher Education: even a small lapse, such as missing eyelid or eyebrow movement, led participants to suspect a character of "aggressive tendencies". — [Times Higher Education](https://www.timeshighereducation.com/node/78783)
- Tinwell (2021 interview): to make a zombie-type character more uncanny, "reduce movement in the upper face, including the eyes, the eyebrows and the forehead"; lip-speech desynchrony also increases uncanniness. — [The Naked Scientists](https://www.thenakedscientists.com/node/199164)
- Duchenne marker (AU6, orbicularis oculi with AU12): a meta-analysis (Gunnery & Ruben 2016, cited here secondarily) found that people showing Duchenne smiles are rated more positively and as more sincere. — [Frontiers in Psychology 2020 (secondary citation)](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2020.01126/full)
- Krumhuber and colleagues: perceived intensity does not fully explain the Duchenne effect; the AU6 marker makes "a unique direct contribution to the perceived genuineness of smiles". — [Krumhuber et al., accepted manuscript, UCL](https://discovery.ucl.ac.uk/10111350/9/Krumhuber_20200306_AU6ms_VersionAccepted.pdf)
- Etcoff et al. (2021) temporarily paralysed the lateral orbicularis oculi with botulinum toxin: smiles produced while the muscle was still active were rated more felt, spontaneous, intense and happier. — [Etcoff et al. 2021, UCL](https://discovery-pp.ucl.ac.uk/10120320/1/Etcoff%20et%20al%282021%29.pdf)
- Counterpoint: AU6 may mainly signal higher intensity rather than spontaneity, because strong negative expressions also contain AU6. — [Frontiers in Psychology 2020](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2020.01126/full); an Affective Science review concludes that the presence or intensity of eye constriction is not enough on its own to infer positive emotion. — [Affective Science, "Reconsidering the Duchenne Smile"](https://doi.org/10.1007/s42761-020-00030-w)
- On robots specifically: in an ICSR 2024 study (N = 305; Mishra, Skantze, Hagoort, Verdonschot), recognition dropped for both humans and robots when only the eye region was visible, and with eye region only, humanlike robot faces were recognised significantly better than mechanical-looking ones. The faces were back-projected animated faces, not mechanical ones. — [Mishra et al., arXiv 2410.14337](https://arxiv.org/abs/2410.14337)

### Inferences
- The two cheapest high-value channels are the brows (sadness, fear, surprise, anger) and the lip corners plus jaw (happiness, surprise, speech). A face that has only one of the two regions loses about half the basic-emotion space.
- AU6 (cheek raise / lower-lid narrowing) is the one "secondary" AU with direct evidence that it changes how genuine an expression feels. On a servo budget it can be approximated by raising the lower lids and tightening the eye aperture, which an eye mechanism with lower lids may already provide at zero extra actuators.
- For a Frankenstein character the Tinwell result runs both ways: a deliberately frozen upper face reads as menacing and corpse-like, while a moving upper face reads as alive and sympathetic. Brow and lid DOFs give the performance control over that dial.

### Gaps
- Original Blais et al. 2012 and Calder et al. 2000 papers were not opened; their claims come via secondary citations.
- No source found that ranks single AUs by perceptual weight in a way that gives numbers per AU (e.g. recognition loss when AU4 alone is removed) for a physical face.
- No perception study found isolating AU10 (sneer), AU14 (dimpler, smirk) or AU15 (lip corner depressor) individually on a robot.

## 2. Actuator counts and DOF layouts of landmark robot faces

### Takeaway
Research android faces cluster between about 7 and 39 head DOF, with most expressive research heads at 20 to 35. The DOFs nearly always go first to brows, eyelids, eyes, jaw and lip corners, then to cheeks and lip shape, and only the largest systems add nose wrinkle, lip funneler and tongue. Many published counts are inconsistent across sources, and some commercial figures are marketing.

### Cited Findings

Comparison table from Yang, Sato et al. (RIKEN / Kyoto, arXiv 2301.05620, Jan 2023), "head DOF" column: Nikola 35 (child); Kobayashi, Hara et al. face robot (1994) 24; ROMAN 21; SAYA 24 (5 basic emotions); Albert HUBO 31 (child-size face, Hanson); Hashimoto et al. life-mask face robot (2008) 39; Geminoid F 12; FACE (Mazzei, Lazzeri, Hanson, De Rossi) 32; Lin et al. simplified face robot (Robotica 2016) 7; EveR 16; XIN-REN 7; EVA 25; EVA 2.0 25. — [Yang et al. 2023, arXiv](https://arxiv.org/abs/2301.05620)

Kobayashi and Hara face robots (1990s to 2000s, Tokyo University of Science)
- 1994 paper (Journal of the Robotics Society of Japan 12(1)): face robot showing the 6 basic emotions, 24 head DOF per the Yang table. — [Yang et al. 2023](https://arxiv.org/abs/2301.05620)
- The group used flexible micro-actuators to move control points corresponding to FACS action units; the Mark I face used pneumatic air cylinders, a later version used shape-memory alloy (SMA) (search summary of Hara, Akazawa & Kobayashi, IEEE 2001). — [IEEE record](https://search.isc.ac/inventory/49/2215347.htm)
- SMA lacked power and speed, so the third-generation face moved to air-tube actuators driven by pressurised air (search summary of an ITE technical report). — [ITE Technical Report, J-STAGE](https://www.jstage.jst.go.jp/article/itetr/25.52/0/25.52_47/_article/-char/en)

SAYA (Hashimoto, Kobayashi et al., 2006)
- 19 control points on the face, chosen according to FACS, combined to produce expressions (search summary; which Fuji Press record holds the sentence was not verified). — [Fuji Press, Journal of Robotics and Mechatronics](https://www.fujipress.jp/?p=7815)
- 24 head DOF, 5 basic emotions per the Yang table. — [Yang et al. 2023](https://arxiv.org/abs/2301.05620)
- A SAYA paper figure is labelled with a McKibben artificial muscle; actuator type for all points not confirmed (search summary). — [Fuji Press](https://www.fujipress.jp/?p=7815)

WE-4RII (Waseda, Takanishi lab, 2004)
- Face DOF: eyebrows 4 DOF each (8 total, flexible sponge brows), eyelids 6, eyeballs 3, lips 4 (spindle-shaped springs pulled from 4 directions), jaw 1. That is 22 face DOF. The eyeball pitch axis mechanically couples the upper-eyelid opening. Total robot DOF usually given as 59; one Japanese source says 56 driven by 27 servo motors (search summary). — [Takanishi, Humanoids 2004 workshop PDF](https://archive.iar.kit.edu/workshops/humanoids2004/Takanishi.pdf); [Waseda repository thesis](https://waseda.repo.nii.ac.jp/record/21255/files/Honbun-4511_10.pdf)

Geminoid F (ATR / Osaka, Ishiguro, 2010)
- 12 DOF total, all pneumatic: 7 face, 3 neck, 2 body (1 chest, 1 spine); can smile and frown, blink and "breathe" autonomously. — [Robots guide (IEEE Spectrum), Geminoid F](https://robotsguide.com/robots/geminoidf)
- Design goal was a wide range of expression with far fewer actuators than Geminoid HI-1, which has 50 actuators (Wikipedia, search summary). — [Wikipedia, Telenoid R1](https://en.wikipedia.org/wiki/Telenoid_R1)
- Recognised for 6 basic emotions in Becker-Asano & Ishiguro (2011) with intercultural differences; numbers not retrieved. — [Becker-Asano & Ishiguro 2011, ResearchGate](https://www.researchgate.net/publication/231157453_Intercultural_Differences_in_Decoding_Facial_Expressions_of_the_Android_Robot_Geminoid_F)

ERICA (Ishiguro lab, 2015)
- 44 pneumatic DOF total across head, neck, arms and waist (lab page); face 13 DOF (Robots guide). — [Ishiguro Lab robots](https://eng.irl.sys.es.osaka-u.ac.jp/robot); [Robots guide, Erica](https://robotsguide.com/robots/erica)

Affetto (Osaka, Ishihara and Asada; first generation 2011, second 2018)
- 2018 face: 22 DOF, all pneumatic (linear cylinders and rotary vane actuators); more actuators than the 2011 model. — [Ishihara et al. 2018, Frontiers in Robotics and AI, ResearchGate](https://www.researchgate.net/publication/328460909_Identification_and_Evaluation_of_the_Face_System_of_a_Child_Android_Robot_Affetto_for_Surface_Motion_Design)
- 116 facial points tracked in 3D and grouped into "deformation units" to model how each actuator moves the skin; balancing applied force against skin adjustment was the main difficulty. — [Osaka University press release 2018](https://resou.osaka-u.ac.jp/en/research/2018/20181114_1)
- Follow-up (Ishihara, Iwanaga & Asada, Frontiers in Robotics and AI 2021): compared five android faces with human adult males by motion capture (6 IR cameras, 120 fps). Android "flow lines" in the eye and forehead areas were almost straight, human ones curved, and upper-face skin undulation differed; the authors propose redesigning skin flow to match human patterns to reduce discomfort. — [TechXplore summary](https://techxplore.com/news/2021-03-analysis-human-android.amp)

Nikola (RIKEN Guardian Robot Project, published 2022)
- 35 pneumatic actuators: 29 for facial muscle actions, 3 for head movement, 3 for the eyeballs; placement follows FACS. — [Sato et al. 2022, Frontiers in Psychology](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full); [RIKEN press release](https://www.riken.jp/en/news_pubs/research_news/pr/2022/20220210_1/index.html)
- A FACS-certified coder confirmed 17 AUs: 1, 2, 4, 5, 6, 7, 10, 12, 14, 15, 16, 18, 20, 22, 25, 26, 43. AUs 9 (nose wrinkler), 17 (chin raiser) and 23 (lip tightener) were not implemented "owing to the technical limitations of the silicone skin", and the coder found AU6 and AU7 hard to tell apart. — [Sato et al. 2022](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full)
- Actuator list (Yang et al. 2023, Table II, the 24 actuators used for optimisation): per side L and R, upper lid raiser, cheek raiser/lid tightener, outer brow raiser, cheek raiser, inner brow raiser, brow lowerer, cheek puller, lip corner puller, lip corner depressor, lip stretcher; plus lip funneler top and bottom, nose wrinkler and jaw dropper. Note the conflict: an actuator is labelled "nose wrinkler", but Sato et al. report AU9 was not produced. — [Yang et al. 2023](https://arxiv.org/abs/2301.05620)

Hanson Robotics
- Sophia: 33 DOF in head and face per a 2024 paper: 5 motors in the brow, 11 for blinking and eye movement, 2 in the nose, 14 for "mouth, tongue, jaw, and surrounding muscles" (these four groups sum to 32, so one DOF is unaccounted for); motor-driven cords anchored under Frubber skin. — [Sophia-in-Audition, arXiv 2402.06978](https://arxiv.org/html/2402.06978)
- Other sources give 36 head-and-neck DOF within 83 total (secondary spec aggregators). — [Humanoid Index, Sophia](https://humanoid-index.pages.dev/robots/sophia); [Wevolver spec](https://www.wevolver.com/specs/sophia-a-realistic-humanoid-robot)
- Albert HUBO / Einstein face: "32 DC gearmotors" for facial muscle movement, pulling linkages attached to the skin (2010 trade article). The Yang table lists Albert HUBO at 31 head DOF. — [Automate.org 2010](https://www.automate.org/motion-control/industry-insights/servo-motors-give-robots-human-face); [Yang et al. 2023](https://arxiv.org/abs/2301.05620)
- Philip K. Dick android: no DOF count found (see Gaps).

Engineered Arts Ameca / Mesmer (2021 onward)
- Engineered Arts' own documentation for "Mesmer Full Size Gen 2" states 61 actuated DOF in total (search summary; the page body did not load for a direct read). — [Engineered Arts docs](https://docs.engineeredarts.co.uk/guide/reference/hardware/mesmer_full_size_gen2)
- "27 DOF in the face" is widely repeated (brows, eyelids, eyes, cheeks, nose, lips, jaw) but no official source was found for it. — [AI Wiki, Ameca](https://aiwiki.ai/wiki/engineered_arts_ameca)
- Conflicting counts: an arXiv facial-imitation benchmark gives Ameca "32 DoFs including facial actuators and head/neck movements" with 30 control values; a review site says 52 DOF. — [X2C benchmark, arXiv 2505.11146](https://arxiv.org/pdf/2505.11146); [Robozaps review (low reliability)](https://blog.robozaps.com/b/engineered-arts-ameca-review)
- A peer-reviewed 2026 study states that the Ameca it used has 13 controllable facial actuators under the skin (exact list in its supplementary table). — [Schwarz et al. 2026, Frontiers in Robotics and AI](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2026.1798227/full)
- Ameca Gen 3 was shown at ICRA 2025; its face configuration may differ (search summary). — [AI Wiki, Ameca](https://aiwiki.ai/wiki/engineered_arts_ameca)

Disney
- A-1000 platform (Walt Disney Imagineering, all-electric): Hondo Ohnaka (Galaxy's Edge, 2019) has 51 functions, 10 of them in the face/head. — [Laughing Place 2019](https://www.laughingplace.com/w/news/2019/02/28/hondo-animatronic-revealed-for-star-wars-galaxys-edge-at-disney-parks/); [FIRST community article](https://community.firstinspires.org/disney-excites-park-guests-with-life-like-animatronics); [WDI A-1000 page](https://sites.disney.com/waltdisneyimagineering/a-1000/)
- The Na'vi Shaman (Pandora, 2017) has 40 functions in the face per WDWNT, about 45 in the head per an IEEE Potentials timeline (conflict). — [WDWNT 2019](https://wdwnt.com/2019/02/photos-video-hondo-audio-animatronic-from-smugglers-run-in-star-wars-galaxys-edge-in-action-list-of-batuus-major-aa-figures/); [IEEE Potentials 38(5) timeline listing](https://www.dix-project.net/item/4774/ieee-potentials-issue-38-5-walt-disney-audio-animatronics-timeline)
- Disney Research "face cloning" (2012, dated): measured silicone elasticity, simulated the skin under the actuators, and tuned skin thickness per region before injection-moulding it; stated next steps were multi-layer skin and more actuators "to give more degrees of freedom". — [ISPR summary 2012](https://ispr.info/2012/08/20/disney-develops-face-cloning-technique-for-animatronics)
- Disney Research "Realistic and Interactive Robot Gaze" (2020): skinless humanoid bust focused on gaze behaviour (saccades, attention habituation, per-actuator motion bandwidth). — [Disney Research](https://la.disneyresearch.com/?p=9313)

Columbia Creative Machines Lab
- Eva (HardwareX 2020; learned control at ICRA 2021): 25 "muscles" as servo motors, 12 of them facial, giving up to 15 mm of skin displacement. The mask mechanism uses 12 MG90S servos in two 3D-printed servo banks, steel wires in Teflon Bowden tubes, a custom silicone mask and a 3D-printed skull; it shows the 6 basic emotions. — [Faraj et al., HardwareX, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041256); [Columbia press release](https://www.engineering.columbia.edu/press-release/the-robot-smiled-back)
- Emo (Hu, Chen, Lin, Wang, Wang, Mehlman, Lipson; Science Robotics 9(88), 2024): 26 actuators under silicone skin, cameras in the pupils; learned to predict a human smile about 840 ms before it happens and smile at the same time. No speech in the published version. — [Columbia Engineering news 2024](https://engineering.columbia.edu/news/robot-can-you-say-cheese)

Recent systems (2024 to 2026)
- Morpheus (Zhang et al., RSS 2025, arXiv 2507.16645): hybrid actuation, rigid linkages for eyes and mouth and strings (tendons) for nose and cheeks "for subtle microexpressions"; speech-to-blendshape network; hardware open-sourced. Actuator count not stated in the abstract. — [Morpheus, arXiv](https://arxiv.org/abs/2507.16645)
- AheadForm Origin M1 (China, video Sept/Oct 2025): "up to 25 micro-motors" for facial actuation, RGB cameras in the pupils; one outlet says 25 to 42 brushless micro-motors and about USD 150,000. These are marketing or press figures, not verified specs. — [Live Science](https://www.livescience.com/technology/robotics/chinese-company-develops-creepy-ultra-lifelike-robot-face-watch-it-blink-twitch-and-nod); [Oddity Central](https://www.odditycentral.com/?p=89948); [Mike Kalil blog](https://mikekalil.com/blog/aheadform-xuan-origin-m1/)
- AheadForm Origin F1: a product page lists 26 DOF (search summary; do not transfer to M1). — [Mike Kalil blog](https://mikekalil.com/blog/aheadform-xuan-origin-m1/)
- Ex-Robots (Dalian, Reuters, June 2024): humanoid faces driven by many miniaturised motors packed around the head; mainly museum exhibits; 1.5 to 2 million yuan each. No actuator count published. — [The Star / Reuters 2024](https://www.thestar.com.my/tech/tech-news/2024/06/12/chinas-ex-robots-develops-humanoids-with-enhanced-facial-movement); [ThePrint](https://theprint.in/tech/chinas-ex-robots-develops-humanoids-with-enhanced-facial-movement/2126146)

### Inferences
- Common core across almost every system, from WE-4RII to Nikola to Sophia: eyes (pan/tilt), upper lids, brows split into inner and outer or with several points per side, jaw, and lip corners up and down. This is the "consensus" budget of about 15 to 20 DOF.
- The next tier, added by the 25 to 35 DOF heads (Nikola, Sophia, Emo, Eva, AheadForm), is cheeks (AU6, AU13), lip stretcher (AU20), lip funneler or pucker (AU18/22), upper-lip raiser (AU10) and nose (AU9). Nikola shows these are the DOFs that silicone skin defeats first.
- Eva is the closest analogue to this hobby head: 12 MG90S face servos on Bowden cables, a 3D-printed skull and a silicone mask, about 15 mm maximum skin travel. That puts a realistic hobby ceiling at roughly a dozen face servos before cable routing and skin stiffness become the limit.
- Disney's choice for Hondo (10 face functions out of 51) suggests that a theme-park character built to read at a distance and in performance spends more on body and head than on fine face DOF; Disney spends 40 or more on the face only for hero close-up figures (the Shaman).
- Pneumatics dominate the Japanese androids (Geminoid, ERICA, Affetto, Nikola) for quiet and smooth motion; servo or gearmotor systems (Hanson, Eva, Emo, Ameca, AheadForm) dominate the rest. Servo noise is a known cost on hobby builds (Nikola's quietness is cited as an advantage of air).

### Gaps
- Kobayashi and Hara's exact actuator count and AU list for the 1990s faces (the "18 control points" figure often quoted) could not be confirmed.
- WE-4RII figures come from search summaries of Waseda documents, not a full read.
- Emo's per-region DOF breakdown, Ameca's official face DOF list, and Sophia's missing 33rd DOF were not found.
- Philip K. Dick android DOF count: not found. Kismet: a USPTO patent text surfaced in search calls it a 15-DOF head, but it was not opened and other counts circulate; treat as unverified.
- Furhat: no primary source retrieved on its projected-face parameters in this round. Mishra et al. (2024) tested back-projected animated faces of the kind Furhat uses, and found them comparable to human faces in expressiveness, but the paper page does not name the robot.
- Disney's "realistic humanoid" research faces beyond 2012 (face cloning) and 2020 (gaze): no newer face-DOF publication found.

## 3. Evidence on minimum DOF sets and low-DOF versus high-DOF faces

### Takeaway
No study was found that ablates DOFs one by one on the same physical face. The indirect evidence is consistent: faces with roughly 7 to 13 facial DOF convey happiness, surprise and sadness reasonably but lose anger, disgust and contempt, while low-DOF bodies convey arousal better than exact emotion labels. Intensity and skin behaviour matter as much as DOF count.

### Cited Findings
- Ameca with 13 controllable facial actuators, transferring captured human expressions (N = 40, 2026): correct recognition human vs virtual avatar vs physical robot was surprise 87.5 / 57.5 / 65%, fear 45 / 27.5 / 57.5%, anger 65 / 40 / 12.5%, disgust 60 / 10 / 22.5%. Reported drops human to robot: joy −60 points, sadness −52.5. The authors blame "a limited number of movable components" and limited "facial resolution", and name anger, disgust and contempt as hardest. The paper has internal inconsistencies between its abstract and its stated differences. — [Schwarz et al. 2026, Frontiers in Robotics and AI](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2026.1798227/full)
- Nikola (29 facial actuators, 17 AUs): all six basic emotions recognised above chance; surprise, sadness and happiness better than disgust, fear and anger. Happiness 90.0% for Nikola vs 98.2% for human faces, gap attributed mainly to "low facial expression intensity". — [Sato et al. 2022](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full)
- On the same 35-actuator Nikola, Bayesian optimisation of 24 actuators (14 symmetric control dimensions) raised human ratings of anger, disgust, sadness and surprise over the expert-designed FACS-prototype expressions; happiness was rated higher for the hand-built prototype. The authors note asymmetric expressions were excluded for simplicity and might be more convincing. — [Yang et al. 2023](https://arxiv.org/abs/2301.05620)
- Very low DOF faces exist and are claimed to show basic emotions: Lin et al.'s "expressional simplified mechanism" face (Robotica 2016) and XIN-REN at 7 DOF; Geminoid F at 7 face DOF; EveR at 16. — [Yang et al. 2023, Table I](https://arxiv.org/abs/2301.05620); [Robots guide, Geminoid F](https://robotsguide.com/robots/geminoidf)
- A design methodology for low-DOF robot faces (Shayganfar, Rich, Sidner, search summary) predicts which emotions will be confused from which AUs the robot's DOF can cover; the observed confusion matrix agreed qualitatively with the predictions. — [ResearchGate](https://www.researchgate.net/publication/261353840_A_design_methodology_for_expressing_emotion_on_robot_faces)
- Reachy Mini (no face; head and antennas; arXiv May 2026, N = 100, 10 clips): discrete emotion recognition was modest, but arousal was still perceived when labels were missed. — [Rogel, Yadollahi & Laban, arXiv 2605.12786](https://arxiv.org/abs/2605.12786)
- A 13-DOF "hybrid-face" robot paper argues for adding pupil dilation as an extra expressive channel (search summary). — [arXiv 2012.04511](https://arxiv.org/pdf/2012.04511)
- An ambiguous android facial expression is perceived more clearly when body posture and movement are added (PLoS ONE 2021, search summary). — [PLoS ONE via DOAJ](https://doaj.org/article/8182180658b04458a0e72ee78d19c6c3)

### Inferences
- Anger and disgust are the expressions that low-DOF faces lose first; they need brow lowerer (AU4), lid tightener (AU7), upper-lip raiser (AU10), nose wrinkle (AU9) and lip press (AU23/24). For a monster character anger and disgust are core, so AU4 and an AU10 "snarl" should rank higher for this project than for a generic social robot.
- Low intensity, not only missing AUs, is a repeated cause of poor recognition (Nikola). Getting full travel out of each DOF through a soft skin is worth as much as adding DOFs.
- Expert-designed symmetric FACS poses are not the ceiling: tuning actuator mixes against human or machine ratings improved four of six emotions on Nikola.

### Gaps
- No controlled ablation (same robot, DOFs disabled one at a time, recognition measured) was found. This is the biggest gap for ranking DOFs by expressive value per actuator.
- Recognition percentages for Geminoid F, SAYA, WE-4RII, Eva and Emo were not retrieved.

## 4. Left/right independence, lower eyelids, cheek raise and nasolabial folds

### Takeaway
Direct robot evidence is thin. The strongest supported item is AU6 (cheek raise with eye narrowing), which measurably raises perceived genuineness of smiles in humans. Most high-end faces (Nikola, Sophia, WE-4RII) give brows, cheeks and lip corners independent left and right actuators, but no study was found that measures what asymmetry adds to lifelikeness on a robot.

### Cited Findings
- Nikola's actuator set is bilateral for every brow, lid, cheek and lip-corner function (separate L and R actuators), with central actuators only for lip funneler, nose wrinkler and jaw. — [Yang et al. 2023, Table II](https://arxiv.org/abs/2301.05620)
- Yang et al.: "Humans often exhibit asymmetrical facial expressions"; Nikola can produce them, but they were excluded from optimisation for simplicity, and the authors suggest asymmetric expressions might be more convincing. — [Yang et al. 2023](https://arxiv.org/abs/2301.05620)
- WE-4RII gives each eyebrow 4 DOF and has 6 eyelid DOF, so independent left and right brows and lids (search summary). — [Takanishi, Humanoids 2004](https://archive.iar.kit.edu/workshops/humanoids2004/Takanishi.pdf)
- AU6 (cheek raiser) produces eye-corner wrinkles that help recognition of happy and sad expressions; Nikola's silicone skin could not form them well, and AU6 and AU7 were hard to distinguish on it. — [Sato et al. 2022](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full)
- Duchenne evidence (orbicularis oculi active → smiles rated more felt, spontaneous and happy). — [Etcoff et al. 2021](https://discovery-pp.ucl.ac.uk/10120320/1/Etcoff%20et%20al%282021%29.pdf); [Krumhuber et al.](https://discovery.ucl.ac.uk/10111350/9/Krumhuber_20200306_AU6ms_VersionAccepted.pdf)
- Asynchrony between face parts in dynamic expressions increased perceived uncanniness for human and android faces (Diel et al., BMC Research Notes 2023). — [RIKEN news](https://grp.riken.jp/en/news/20231220/)
- In a Scientific Reports study (2023, 75 participants), asynchrony reduced ratings of human expressions but did not affect android expressions, suggesting human faces are processed configurally by synchrony and android faces are not. — [RIKEN news](https://grp.riken.jp/en/news/20231007/)
- Silicone skin limits wrinkle and fold formation: Nikola could not do AU9, AU17 or AU23 for that reason. — [Sato et al. 2022](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full)
- Disney tuned silicone thickness region by region from simulation to get the right deformation under given actuators. — [ISPR 2012](https://ispr.info/2012/08/20/disney-develops-face-cloning-technique-for-animatronics)
- Morpheus moved nose and cheek actuation to strings (tendons) specifically to get "subtle microexpressions" in a constrained space. — [Morpheus, arXiv](https://arxiv.org/abs/2507.16645)

### Inferences
- Asymmetry costs no extra actuators if each side already has its own servo (as with two independent brow mechanisms); it costs only software. Given that, a unilateral brow raise, a half-smile (one lip corner, AU12 or AU14 unilateral, the FACS marker of contempt) and a wink are among the highest "fun per actuator" moves available, because the hardware is already paid for. Recognition studies do not measure fun; this is a design judgement.
- The lower lid is the cheapest route to AU6/AU7: raising it narrows the eye, which reads as a Duchenne smile, a squint of anger or suspicion, or pain, depending on brow and mouth.
- Nasolabial folds and nose wrinkles depend more on skin design (thinner zones, fold lines moulded in, anchor points) than on extra actuators. A cheek or upper-lip pull that lands on a pre-formed crease line is the usual hobby workaround (inference from the Disney and Nikola findings, not tested here).
- Because asynchrony is linked to uncanniness, asymmetric moves should be deliberate and brief, while symmetric expressions should keep the brows, lids and mouth onsets in step.

### Gaps
- No study found that measures lifelikeness or likeability gains from asymmetric robot expressions (smirk, single raised brow, wink).
- No robot study found isolating lower-eyelid motion or nasolabial-fold formation.

## 5. Head and neck motion, and jaw versus lip separation

### Takeaway
Head motion changes perceived emotion, especially valence and arousal, and adds naturalness during speech; robot studies show nods, shakes and tilts all shift perception and that their timing relative to speech matters. Where face and head tilt were compared directly, the face (smile) had the larger effect. Nearly every landmark head budgets 3 neck DOF (5 on Ameca). Jaw and lips are separated in all higher-DOF systems.

### Cited Findings
- Busso, Deng, Grimm, Neumann & Narayanan (IEEE TASLP 15(3), 2007): head motion during emotional speech differs significantly from neutral speech in activation, range and velocity, and perception tests showed that head motion modifies the emotional perception of facial animation, especially in valence and activation. — [Busso et al. 2007 PDF](https://msp.utdallas.edu/publications/Busso_2007.pdf)
- A 2024 International Journal of Social Robotics study with a minimal-DOF robot head found that nodding, shaking and tilting all significantly affected user perception, and that moving the head before speaking affected perceived naturalness. — [Springer IJSR 2024](https://link.springer.com/article/10.1007/s12369-024-01196-0)
- Saerbeck & Bartneck (2010), iCat with neutral face: acceleration and curvature of head motion both had a significant effect on perceived affect. — [Bartneck publications page](http://www.bartneck.de/publications/2010/perceptionAffectElicitedRobotMotion/index.html)
- Head tilt raised attributed human-likeness, cuteness and "spine-tinglingness" over an upright posture; in a related experiment crossing smile speed with head tilt, head posture had a weaker effect than smiling (RO-MAN 2024, search summary). — [ResearchGate, "The Feeling of Kawaii toward a Robot's Head-Tilting Motion"](https://www.researchgate.net/publication/385416056_The_Feeling_of_Kawaii_toward_a_Robot's_Head-Tilting_Motion_Effects_of_Speed_Direction_and_Accompanying_Hand_Gestures)
- Neck budgets: Nikola 3 head actuators; Geminoid F 3 neck DOF; Ameca 5 neck DOF in secondary breakdowns. — [Sato et al. 2022](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full); [Robots guide, Geminoid F](https://robotsguide.com/robots/geminoidf); [AI Wiki, Ameca](https://aiwiki.ai/wiki/engineered_arts_ameca)
- Low-DOF bodies without faces still carry arousal through motion. — [Reachy Mini, arXiv 2605.12786](https://arxiv.org/abs/2605.12786)
- Jaw vs lips: WE-4RII has a 1-DOF jaw plus 4 lip DOF; Nikola has a jaw dropper plus separate lip corner puller, depressor, stretcher and funneler actuators; Sophia has 14 actuators for mouth, tongue, jaw and surrounding muscles. — [Takanishi 2004](https://archive.iar.kit.edu/workshops/humanoids2004/Takanishi.pdf); [Yang et al. 2023](https://arxiv.org/abs/2301.05620); [Sophia-in-Audition](https://arxiv.org/html/2402.06978)
- Nikola's AU list includes AU25 (lips part) and AU26 (jaw drop) as separate units, coded together as 25+26. — [RIKEN It Ain't Magic](https://itaintmagic.riken.jp/hot-off-the-press/introducing-nikola-the-emotional-android-boy/)
- Lip-speech desynchrony increases uncanniness (Tinwell). — [The Naked Scientists](https://www.thenakedscientists.com/node/199164)

### Inferences
- Per actuator, a neck tilt (roll) and nod (pitch) probably buy more "alive" than any single additional facial DOF beyond the core set, because they act during every second of speech and idle, and because Busso shows they shift perceived emotion. A turn (yaw) adds gaze-following with the whole head. This is an inference; no study compares one neck DOF against one face DOF.
- A jaw-only mouth can open and close but cannot form rounded vowels (O, U) or spread lips (E); lip funneler/pucker and lip corner stretch are what make speech read as speech rather than a puppet's flap. Wherever the Cogley mouth already separates lip corners from the jaw, that separation is worth keeping.

### Gaps
- No study found that crosses head-motion DOF with facial DOF on a physical robot face and measures emotion recognition or lifelikeness directly.
- No study found that quantifies jaw-only vs jaw-plus-lips on perceived speech quality for a physical robot.

## 6. DOFs most often reported missing, or causing uncanny or dead-looking faces

### Takeaway
The most common reported failures are: (1) a still or mechanically moving upper face (brows, lids, forehead), (2) skin that cannot wrinkle or fold, so AU9 nose wrinkle, AU6 crow's feet, AU17 chin raise and AU23 lip tightener are lost, (3) low expression intensity and limited range, (4) stiff, slow or poorly timed motion and desynchrony between face parts or between lips and speech, and (5) straight, linear skin flow instead of the curved paths of human skin.

### Cited Findings
- Upper-face stillness (eyelids, brows, forehead) raises uncanniness, especially for fear and surprise. — [Tinwell et al.](https://vbn.aau.dk/ws/files/63140615/Facial_expression_of_emotion_and_perception.pdf)
- Nikola could not produce AU9, AU17 or AU23 because its silicone skin "is less elastic than real human skin and cannot form wrinkles very well", which made disgust harder to identify; happiness intensity was also low. — [Sato et al. 2022](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full); [RIKEN It Ain't Magic](https://itaintmagic.riken.jp/hot-off-the-press/introducing-nikola-the-emotional-android-boy/)
- Nikola's dynamics: naturalness ratings generally fell as speed slowed, but slower onsets were more natural for sadness and faster ones for surprise. — [Sato et al. 2022](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.800657/full)
- Android skin moves along nearly straight lines in the eye and forehead areas, while human skin follows curved paths, and upper-face surface undulation differs; proposed as a cause of discomfort. — [Ishihara et al. 2021 via TechXplore](https://techxplore.com/news/2021-03-analysis-human-android.amp)
- Sophia: actuators cover about half of the ARKit blendshapes; limited motor power restricts how fast and how far expressions change; big smiles and minute expressions are hard; viewers found performances "stiff and mechanical". — [Sophia-in-Audition, arXiv 2402.06978](https://arxiv.org/html/2402.06978)
- Ameca with 13 face actuators: losses blamed on few movable components and limited "facial resolution", worst for anger, disgust and contempt. — [Schwarz et al. 2026](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2026.1798227/full)
- Asynchrony between parts of a dynamic expression increases uncanniness. — [Diel et al. 2023, RIKEN news](https://grp.riken.jp/en/news/20231220/)
- Early SMA face actuators lacked power and speed, forcing a switch to pneumatics. — [ITE Technical Report](https://www.jstage.jst.go.jp/article/itetr/25.52/0/25.52_47/_article/-char/en)
- Missing eyelid or eyebrow movement can make a character read as hostile ("aggressive tendencies"). — [Times Higher Education](https://www.timeshighereducation.com/node/78783)

### Inferences
Candidate DOF ranking for this head, by expressive value per actuator. This synthesises the findings above and is a design judgement, not a measured result. Tier 1 is assumed already present in the planned mechanisms (Cogley EyeMech, Cogley mouth, two MG90S brows); whether a given item is present depends on those mechanisms' actual DOF lists.

| Tier | DOF (FACS) | Why (from the findings) | Cost note |
|---|---|---|---|
| 1 | Eye pan/tilt + upper lids, blink (AU5, AU43) | in every system; upper-face stillness is uncanny | EyeMech |
| 1 | Brow per side, raise/lower (AU1/2 vs AU4) | sadness, fear, surprise, anger are eye/brow-led; upper-face stillness is uncanny | 2 MG90S (in plan) |
| 1 | Jaw (AU26/27) | speech, surprise, fear | mouth mechanism |
| 1 | Lip corners up/down per side (AU12/AU15) | happiness and sadness are mouth-led; L/R gives smirk | mouth mechanism, if present |
| 2 | Lower lids (AU6/AU7 proxy) | Duchenne genuineness, anger squint; no extra servo if EyeMech lower lids exist | software |
| 2 | Inner vs outer brow split (AU1 vs AU2) | sad "worried" brow (AU1+AU4) vs surprised arch (AU1+2); WE-4RII 4/brow, Nikola 3/brow, Sophia 5 brow | +1 servo per brow |
| 2 | Neck nod + tilt (+ turn) | shifts perceived valence/arousal, constant liveliness (Busso; IJSR 2024) | 2 to 3 larger servos |
| 3 | Upper-lip raiser / snarl (AU10), nose wrinkle (AU9) | disgust and anger, the expressions low-DOF faces lose first; key for a monster | skin-limited (Nikola failed AU9) |
| 3 | Lip pucker/funnel (AU18/22) and stretch (AU20) | O/U and E visemes, fear (AU20) | 1 to 2 servos |
| 4 | Cheek puller/raiser separate from lower lid (AU6, AU13) | Nikola, Sophia, Ameca have it; marginal once lower lid moves | tendon-friendly (Morpheus) |
| 4 | Chin raiser (AU17), lip press (AU23/24) | anger/sadness detail; Nikola could not do them in silicone | skin-limited |

- Software-only multipliers: independent L/R use of existing servos (wink, one brow, half-smile), per-emotion onset speed (slow sadness, fast surprise), and keeping face parts in sync with each other and with speech. The findings say these change perception without any new hardware.
- Skin choices interact with DOF value: soft, thin zones and moulded crease lines along curved flow paths are what let AU6, AU9 and AU10 read at all.

### Gaps
- No primary source found that lists the DOFs of Will Cogley's mouth mechanism or EyeMech v3.2 (not researched here; check the project's reference files).
- No study found that measures "fun" or engagement per DOF; the ranking above uses recognition and uncanniness findings as stand-ins.
- No published figure found for skin travel per DOF through Dragon Skin FX-Pro specifically; Eva's 15 mm maximum skin displacement through its silicone mask is the only hobby-comparable number found.
