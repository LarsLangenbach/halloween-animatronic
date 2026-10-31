# LLM-driven robot and avatar facial expression and nonverbal behaviour (2023 to October 2026)

Scope: how LLMs and modern generative models drive faces, and what that says about the split between what the LLM decides and what a local performance engine decides. Notes gathered 2026-10-30. Peer-reviewed work is marked [PEER-REVIEWED]; preprints [PREPRINT]; company documentation [VENDOR DOCS]; press and marketing [MARKETING/PRESS]; aggregator or secondary summaries [SECONDARY].

## 1. Engineered Arts Ameca with GPT models: how expressions are chosen, local vs cloud, published pipeline details

### Takeaway
Engineered Arts has published almost nothing about Ameca's LLM-to-face pipeline. The few primary facts are telling: in 2023 GPT-3 picked the expressions, and GPT-4 was dropped because its latency made the robot feel unresponsive. Expressions come from a library of 50+ hand-authored poses and animations in Tritium, not generated motor trajectories. A 2025 peer-reviewed Ameca study had to play expressions *after* lip-synced speech because the two processes conflicted, and participants found that unnatural.

### Cited Findings
- Official Ameca account (early 2023): "Appropriate facial expressions in this video are selected by GPT3 - we also tried GPT4, the processing time with GPT4 was longer and made Ameca appear less responsive." This is the only first-party statement found on how expressions are chosen. It says GPT *selects* an expression; it does not say whether that happens through tags, function calls or a separate classification call. [MARKETING/PRESS, first-party] — [Ameca on X](https://x.com/AmecaTheRobot/status/1641749840580280321)
- Ameca "comes pre-programmed with over 50 realistic facial expressions". Users design new ones with Tritium's "Poses and Animator" functions, every DoF of eyes, mouth, brows and cheeks can be fine-tuned, base behaviours such as blinking, subtle speaking motion and simulated breathing are configurable, and there is a "library of pre-configured gestures that can be synced with facial expressions". [VENDOR DOCS] — [Engineered Arts: Ameca](https://engineeredarts.com/robots/ameca)
- Wikipedia: Ameca interactions can be run by OpenAI's GPT-3 or by human telepresence. [SECONDARY] — [Wikipedia: Ameca](https://en.wikipedia.org/wiki/Ameca_(robot))
- Third-party claims that Tritium "handles low-level motor control, animation blending, scripted performance, and ... real-time integration with cloud LLMs", that it blends LLM-driven speech against the 50+ pre-authored expressions on the fly, and that "Tritium 3 OS" integrates GPT-4, Claude and Gemini are unofficial summaries. Sources also disagree on facial motor counts (11→27, 27, 52, 61 DoF total). Treat these as unverified. [SECONDARY] — [Ameca - Learn AI wiki](https://ai.miraheze.org/wiki/Ameca); [robotsinlife directory](https://robotsinlife.pages.dev/robots/engineered-arts-ameca); [aiwiki: Engineered Arts](https://aiwiki.ai/wiki/engineered_arts)
- The press reports the speech pipeline as ASR, then the LLM, then TTS "while coordinating appropriate facial expressions"; that is, the LLM runs in the cloud and animation and motor control run locally. [SECONDARY] — [EU Innovation Valley: Talking to AI robots](https://www.euinnovationvalley.de/en/news-events/roboter-ameca); [humanoidapplications](https://humanoidapplications.com/robot/ameca-engineered-arts/)
- Kirjavainen et al., "Exploring Perceptions of Robot Facial Expressions in Service Interactions", Mindtrek '25 (Tampere, 7–10 Oct 2025; published 17 Nov 2025), N = 28, within-subjects, counterbalanced. [PEER-REVIEWED] — [self-archived PDF, Univ. of Lapland](https://lacris.ulapland.fi/ws/files/46321884/3757980.3757996.pdf); [DOI 10.1145/3757980.3757996](https://doi.org/10.1145/3757980.3757996)
  - The dialogue was *scripted*, not LLM-generated: a theatre ticket sale with 6 fixed expression slots per conversation. Condition A used 6 appropriate expressions and condition B 6 inappropriate ones, 12 in total, designed from FACS-informed sources.
  - The authoring path was the Tritium "Sequence Creator", previewed in "Virtual RoboThespian", then uploaded to the robot. "the physical rendering of expressions on the robot was less pronounced compared to their appearance in the virtual preview", so the authors kept only expressions with "a strong and clear physical rendering".
  - "The version of Ameca used in the study was unable to move the corners of its mouth downwards, limiting its capability for sad expressions."
  - Key pipeline constraint: "Rendering facial expressions while lip-syncing with speech often causes conflicts between the two processes. Hence, the facial expressions were shown after the speech had ended."
  - Results: appropriate expressions "significantly enhanced pragmatic aspects of the interaction" (UEQ-S) compared with inappropriate ones. Participants found the delayed expressions unnatural: "The expressions were not correctly timed; they didn't feel authentic" (P4). Incongruent faces made people doubt themselves: "Several times Ameca made a worried, unsure, or startled face, which made me think I'd asked a bad question" (P28). Some found the inappropriate faces "funny" or "like art".
  - The authors call the inability to express during lip-sync "a key limitation" and "a key requirement for the future development of conversational robots".

### Inferences
- Even the best-funded commercial face uses a discrete *library* of authored expressions that the LLM selects from, not LLM-generated motor values. This supports Frank's tag-to-engine design.
- Ameca's GPT-4 vs GPT-3 trade-off is direct evidence that time to response outweighed better expression choices in practice. Spending extra LLM calls on expression selection is costly.
- The Ameca study shows that expression and lip-sync have to share the mouth simultaneously; a "play the expression after the line" design is perceived as wrong. Frank's engine needs a compositor in which the jaw and lip-sync claim the mouth while emotion still drives brows, lids, eyes and mouth-corner offsets during speech.
- Silicone and mechanics damp expressions relative to a virtual preview, so Frank's per-actuator expression gains should be tuned on the physical head and probably exaggerated relative to any on-screen preview.

### Gaps
- No Engineered Arts engineering blog, talk or doc found that says whether current Ameca uses inline tags, OpenAI function/tool calls, or a separate sentiment classifier. docs.engineeredarts.co.uk returned no readable content.
- No published latency budget for Ameca's ASR → LLM → TTS → face chain.
- It is unknown whether the "expressions after speech" limitation in the Mindtrek study comes from Tritium itself or from that study's sequencing setup.

## 2. Academic work: GenEM, Columbia Emo, LLM-to-FACS/blendshape, Furhat + LLM, LLMs outputting valence/arousal or intensities, prosody–face alignment

### Takeaway
The academic pattern from 2023 to 2026 is consistent. LLMs are good at the *social reasoning* layer (which emotion or behaviour fits this moment, given context), and they are unreliable when asked to emit low-level or numeric control directly. Successful systems constrain the LLM to a closed vocabulary of skills, gestures or emotion labels (optionally with an intensity) and leave timing, blending and motor mapping to deterministic or learned lower layers. Separately, learned "self-model" faces (Columbia Emo) show that motor-level realism and lip-sync can be learned from audio and video, without any language model.

### Cited Findings
**GenEM (Mahadevan et al., Google DeepMind, HRI '24, Boulder, 11–14 Mar 2024)** [PEER-REVIEWED]
- The LLM turns a language instruction or social context into *parametrised control code over pre-existing robot skills*, using few-shot chain-of-thought. — [arXiv 2401.14673](https://arxiv.org/pdf/2401.14673)
- The pipeline is a chain of frozen GPT-4 calls (gpt-4-0613, temperature 0): (1) Expressive Instruction Following, which reasons about how a human would express the behaviour; (2) Human-to-Robot Translation onto the robot's affordances; (3) Code Generation over a skill library (Voyager-style small reusable functions); (4) optional Feedback Propagation. — [arXiv 2401.14673v2 HTML](https://arxiv.org/html/2401.14673v2)
- The platform was a mobile robot with a pan/tilt head, base motion, a light strip and speech; Spot and a quadruped in simulation. There was no face. — [arXiv HTML](https://arxiv.org/html/2401.14673v2)
- Results: the multi-step pipeline beat a single-call "instruction → code" ablation (e.g. "Excuse" 5/5 vs 0/5; "Follow" 3/5 vs 0/5). In online video studies (N = 29 and N = 23), GenEM++ was rated better than a professional animator's oracle on 2/10 behaviours and worse on 2/10. Learned skills were reused inconsistently (nodding never used in "Approach"), and removing capabilities led to calls to undefined functions. No latency is reported; the studies were video-based and single-turn. — [arXiv HTML](https://arxiv.org/html/2401.14673v2)
- CACM summary of the design rationale: social reasoning is offloaded to the LLM while "robot code is constrained to safe predefined skills". — [CACM: Teaching robots manners](https://cacm.acm.org/news/teaching-robots-manners)

**Columbia "Emo" (Hu, Chen, Lin, Wang, Wang, Mehlman, Lipson)** [PEER-REVIEWED]
- "Human-robot facial coexpression", *Science Robotics* 9(88), March 2024, DOI 10.1126/scirobotics.adi4724. The head has 26 actuators under silicone skin and cameras in the pupils. Through "self modeling" it learned the motor-command → own-face relationship over a few hours of random babbling in front of a camera. Two networks: one predicts the human's upcoming expression, the other generates motor commands for a target expression. It anticipates a smile about 839 ms before it occurs and smiles simultaneously. It has no verbal or language capability. — [Columbia Engineering news](https://engineering.columbia.edu/news/robot-can-you-say-cheese); [ScienceDaily](https://sciencedaily.com/releases/2024/03/240327154854.htm); [PopSci](https://www.popsci.com/technology/emo-smile-robot-head/)
- Follow-up: "Learning realistic lip motions for humanoid face robots", *Science Robotics*, 14 Jan 2026, DOI 10.1126/scirobotics.adx3017. The robot first learns its own face from thousands of random expressions, then learns the audio → human mouth relation from YouTube talking and singing videos. Combined, it maps incoming audio to motor actions in several languages "without understanding the audio's meaning". Evaluation with ~1,300 volunteers against two other mouth-control methods and an ideal reference; limitations remain for certain sounds. — [TechXplore](https://techxplore.com/news/2026-01-robot-lip-sync-youtube.html); [ScienceDaily](https://www.sciencedaily.com/releases/2026/01/260116035308.htm); [Live Science](https://www.livescience.com/technology/robotics/creepy-humanoid-robot-face-learned-to-move-its-lips-more-accurately-by-staring-at-itself-in-the-mirror-then-watching-youtube)

**LLM + Furhat (Furhat's face is an ARKit-parameterised back-projected face)**
- Mishra, Verdonschot, Hagoort, Skantze, "Real-time emotion generation in human-robot dialogue using large language models", *Frontiers in Robotics and AI*, Dec 2023. GPT-3.5 treated the robot's appraisal as "emotion recognition in conversation", predicting the robot's emotion each turn from the dialogue history and showing it as a Furhat facial expression. N = 47 in a card-sorting game with Neutral, Congruent and Incongruent conditions. Congruent LLM-driven expressions were rated significantly more human-like, emotionally appropriate and positive. Input was text-only. [PEER-REVIEWED] — [PMC10722897](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10722897/)
- FurChat (Cherakara et al., SIGDIAL 2023): one structured prompt (persona, database facts, dialogue history, response format with sample emoticons). The LLM emits an emoticon that is mapped onto Furhat facial gestures. [PEER-REVIEWED] — [arXiv 2308.15214](https://arxiv.org/abs/2308.15214v1); [ACL Anthology](https://aclanthology.org/2023.sigdial-1.55)
- Galatolo & Winkle, "Simultaneous text and gesture generation for social robots with small language models", *Frontiers in Robotics and AI* 12, 16 May 2025, Furhat (face) and Pepper (body). [PEER-REVIEWED] — [Frontiers](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1581024/full)
  - Inline tag format interleaved with speech: `[GEST] ... [GEST]`, carrying a gesture label (e.g. NECK_TILT) plus a parameter such as intensity. This is the same idea as Frank's square-bracket tags.
  - In-context-learning (prompt-only) error rates for Furhat / Pepper: LLaMA 70B 3% / 2%; 8B 27% / 62.2%; 3B 29.3% / 35.7%; 1B 42.5% / 55.2%. Chain-of-thought was worse for small models (8B 57.8% / 49.3%).
  - Overhead vs plain text: ICL 3.3× time; CoT 6.6×; a small trained "gesture head" on the LLM's last hidden state costs only 1.02× time. The head constrains output to valid gestures and trains in about 5 minutes on consumer hardware.
  - Caveats: ground truth was the 70B model's own CoT output (agreement with a proxy, not human judgement), there was no human evaluation, and on the robot Furhat sometimes produced odd combinations such as smiling while talking.
  - Authors' conclusion: prompt engineering alone is insufficient, especially for small models.
- Abbo, Pinto-Bernal, Catrycke, Belpaeme, "Fast Multi-Party Open-Ended Conversation with a Social Robot", Ghent University – imec, arXiv 2503.15496 (v2 revised Dec 2025, under review). GPT-3.5 streamed and was chunked into sentences on ".", "!" or "?" for TTS. Gaze and head turns were driven by face-tracking and perception modules, not by the LLM; a "brow raise" played as feedback when a transcription arrived. Mean response delay was 1.35 s (SD 0.55), sometimes nearly 5 s; the LLM's mean share was 0.76 s. Gaze that didn't match the verbal addressee confused participants, and participants asked for clearer turn-boundary signals. [PREPRINT] — [arXiv 2503.15496v2](https://arxiv.org/html/2503.15496v2)
- An open-source library, "expressive-furhat" (PyPI v0.1.0; paper credited to Abbo, Janssens, Van de Vreken, Belpaeme): a "multi-stage LLM pipeline that detects mood changes and generates appropriate facial expressions and head movements", plus a gaze-aversion thread. It is a drop-in replacement for furhat-remote-api and runs on OpenAI or local Ollama. [SECONDARY: package description] — [PyPI: expressive-furhat](https://pypi.org/project/expressive-furhat/)
- Furhat's commercial "FurhatAI Creator" lists "Expressivity Controls" with Azure OpenAI 4o-mini in its higher tier. How expressions are invoked is not public. [VENDOR DOCS] — [FurhatAI Creator](https://www.furhatrobotics.com/de/furhat-creator)
- Furhat's face uses Apple ARKit parameters, and researchers mapped FACS AUs onto ARKit parameters to render basic emotions (arXiv 2410.14337, 2024). [PREPRINT] — [arXiv 2410.14337](https://arxiv.org/pdf/2410.14337)

**LLM → FACS / AU / blendshape**
- No paper found in which an LLM emits FACS AU or ARKit blendshape sequences directly for a physical robot face. The nearest work: AU-driven robot expression synthesis (IEEE T-RO 2024, DOI 10.1109/TRO.2024.3422051, no LLM stated); FineFace AU-conditioned image generation covering "focused, squinting, confused, skepticism" (arXiv 2407.20175, Jul 2024); AUHead AU-controlled emotional talking heads (arXiv 2602.09534, Feb 2026); VL-FAU AU recognition with language descriptions (MM '24). — [T-RO 2024](https://dl.acm.org/doi/abs/10.1109/TRO.2024.3422051); [FineFace](https://arxiv.org/abs/2407.20175); [AUHead](https://arxiv.org/pdf/2602.09534); [VL-FAU](https://arxiv.org/pdf/2408.00644)
- A 2026 robot-receptionist head (Fonseka et al., IEEE/ASME AIM 2026, arXiv 2607.17042, Jul 2026): 21 DoF under silicone skin, with Llama + Whisper for language and SCRFD/ArcFace/ByteTrack for face tracking. Mean human-likeness 4.13/5. The abstract does not describe the LLM-to-expression link. [PREPRINT, accepted] — [arXiv 2607.17042](https://arxiv.org/abs/2607.17042)

**LLMs and valence/arousal numbers**
- Mehra, Laban, Gunes (ACM, 2025; arXiv 2502.06875): given valence/arousal values, LLMs "struggle to classify VA values into discrete emotion categories, particularly for emotions beyond basic polarities". [PEER-REVIEWED] — [ACM DOI 10.1145/3719160.3737618](https://dl.acm.org/doi/10.1145/3719160.3737618); [arXiv 2502.06875](https://arxiv.org/pdf/2502.06875)
- "Don't Get Too Excited — Eliciting Emotions in LLMs" (arXiv 2503.02457, 2025): LLM-driven virtual humans induced the intended *valence* in users, but *arousal* was "not evoked but could be recognized". [PREPRINT] — [arXiv 2503.02457](https://arxiv.org/pdf/2503.02457)
- CETalk (arXiv 2608.15110, Aug 2026): continuous valence–arousal control for audio-driven 3D talking heads. Its authors note that the VA framework naturally supports smooth transitions between emotional states. [PREPRINT] — [arXiv 2608.15110](https://arxiv.org/pdf/2608.15110)
- No study found in which an LLM outputs continuous VA values that then drive a physical robot face, evaluated against label-based control.

### Inferences
- GenEM's multi-call, code-generating approach (GPT-4, no latency reported) is too slow for per-utterance live use. It fits *offline authoring*: an LLM could help draft parametrised expression "skills" for Frank's library, which the live engine then plays.
- Galatolo & Winkle show inline tags with intensities are the established cheap format. A frontier cloud model (Sonnet-class) sits at the 70B end of their error curve (around 3% invalid), but a parser with a closed vocabulary and a neutral fallback is still needed.
- Mehra et al. and the "arousal not evoked" result suggest LLMs handle *categorical* emotional judgements better than numeric affect coordinates. Ask the LLM for a label plus a coarse intensity, and let the engine place it in a continuous space (VA or a per-actuator pose space) and handle transitions.
- Emo shows the most realistic motor-level behaviour came from learned audio/vision → motor models with no language input. The two layers are complementary: language picks the emotion, and signal-level models produce the motion.

### Gaps
- No peer-reviewed comparison of "LLM inline tag" vs "separate emotion classifier on the LLM text" vs "emotion from TTS audio" on the same robot face.
- No paper found that measures TTS-prosody/face emotional alignment on a physical robot (beyond Emo's lip-sync and the speech-driven animatronic work in section 3).
- The full "Expressive Furhat" paper (venue, stages, latency) was not retrieved; the PyPI page did not render.

## 3. Speech-driven facial animation inferring emotion from audio (Audio2Face/Audio2Emotion, EmoTalk, FaceFormer, Audio2Photoreal, ARKit 52) and mapping to physical servo faces

### Takeaway
Industry and academia converged on ARKit-style 52 blendshape coefficients as the intermediate representation between speech and faces. Several 2024–2026 animatronic papers drive physical faces from it, either with learned inverse models (self-model networks) or, for low-DoF heads, with hand-designed piecewise-linear maps per blendshape. NVIDIA's Audio2Face (open-sourced 2025) is the clearest industrial template for the LLM/engine split: emotion is inferred from audio *and* blended with an externally supplied "preferred emotion", with explicit strength, contrast, smoothing and max-emotion controls.

### Cited Findings
**NVIDIA Audio2Face-3D / Audio2Emotion** [VENDOR DOCS unless noted]
- NVIDIA open-sourced the Audio2Face models and SDK (trade press, Sept 2025): audio plugins, training framework, sample data, face models and a UE5 plugin. — [ETCentric](https://www.etcentric.org/?p=196138)
- NGC lists Audio2Face-3D v2.3, v3.0 and Audio2Emotion v2.2 as open-sourced, with Hugging Face releases dated 27 Aug 2025. The output is ARKit blendshapes including emotional expression. — [NGC Audio2Face-3D NIM](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/audio2face-3d/1); [build.nvidia.com model card](https://build.nvidia.com/nvidia/audio2face-3d/modelcard)
- Audio2Emotion is a speech-emotion classifier (Wav2Vec2-based per NGC) over 6 classes: anger, disgust, fear, joy, neutral, sadness. Licence: "You may not use this model ... outside of the Audio2Face project" and not "for the purpose of emotion recognition". Commercial use is described inconsistently ("non-commercial" on one NGC listing; "designed for commercial use" on build.nvidia.com). — [NGC](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/audio2face-3d/1); [build.nvidia.com](https://build.nvidia.com/nvidia/audio2face-3d/modelcard)
- Emotion controls (key names differ by version):
  - `emotion_strength` defaults to 0.6 and scales emotion against neutral after blending. The Maya-ACE docs give emotion = strength × (weight × preferred + (1 − weight) × generated).
  - `preferred_emotion_strength` (0–1, default 0.5): 0 means only Audio2Emotion's output is used, 1 means only the preferred (externally supplied) emotion.
  - `emotion_contrast` (default 1, range 0.3–3) widens the spread between emotion values via a sigmoid.
  - Smoothing in v1.0 runs from 0, "no smoothing at all (can be jittery)", to 1, "emotion values not updated over time"; v2.0 uses `live_transition_time`.
  - "Max emotions" caps how many emotions engage, prioritised by strength.
  - [A2F-3D container config 1.3](https://docs.nvidia.com/ace/audio2face-3d-microservice/1.3/text/deployment/container-config.html); [Parameter tuning 1.0](https://docs.nvidia.com/ace/audio2face-3d-microservice/1.0/text/param-tuning.html); [A2F-3D microservice 2.0](https://docs.nvidia.com/ace/audio2face-3d-microservice/2.0/text/architecture/audio2face-ms.html); [Maya-ACE UI](https://docs.nvidia.com/ace/latest/modules/maya_ace/texts/userinterface.html)

**Academic speech-to-face models**
- EmoTalk (Peng et al., ICCV 2023, pp. 20687–20697): an emotion-disentangling encoder separates content from emotion in speech; the decoder outputs "emotion-enhanced blendshape coefficients" (3D-ETF dataset). Code is public. [PEER-REVIEWED] — [CVF open access](https://openaccess.thecvf.com/content/ICCV2023/html/Peng_EmoTalk_Speech-Driven_Emotional_Disentanglement_for_3D_Face_Animation_ICCV_2023_paper.html); [arXiv 2303.11089](https://arxiv.org/pdf/2303.11089)
- Follow-ups: EmoVOCA (WACV 2025) and PESTalk (ACM MM 2025, personalised emotional styles). [PEER-REVIEWED] — [EmoVOCA](https://openaccess.thecvf.com/content/WACV2025/papers/Nocentini_EmoVOCA_Speech-Driven_Emotional_3D_Talking_Heads_WACV_2025_paper.pdf); [arXiv 2512.05121](https://arxiv.org/pdf/2512.05121v1)
- Audio2Photoreal (Ng et al., Meta Codec Avatars Lab + UC Berkeley, CVPR 2024, arXiv Jan 2024): from dyadic conversation audio it generates face, body and hand motion. Face motion comes from an audio-conditioned diffusion model with a pretrained lip regressor. Body motion uses a VQ transformer for coarse "guide poses" at about 1 fps, then diffusion fills in 30 fps detail. [PEER-REVIEWED] — [CVF](https://openaccess.thecvf.com/content/CVPR2024/html/Ng_From_Audio_to_Photoreal_Embodiment_Synthesizing_Humans_in_Conversations_CVPR_2024_paper.html); [project page](https://people.eecs.berkeley.edu/~evonne_ng/projects/audio2photoreal/)
- FaceFormer (Fan et al., CVPR 2022) predates the window and was not re-verified in this session; it is the usual transformer baseline for audio → 3D face.

**Retargeting to physical (servo) faces**
- Li, Li, Liu, "Driving Animatronic Robot Facial Expression From Speech", IROS 2024 (arXiv 2403.12670, Mar 2024). It is "skinning-centric", with linear blend skinning as the unifying representation for actuation topology, human-expression retargeting and speech-driven motion. It adopts the ARKit standard (minus tongue-out) as the shared human/robot expression space and runs at >4000 fps on an RTX 4090. Code: OpenRoboExp. [PEER-REVIEWED] — [arXiv 2403.12670](https://arxiv.org/abs/2403.12670); [BIGAI PDF](https://www.bigai.ai/wp-content/uploads/2024/10/IROS24_Driving-Animatronic-Robot-Facial-Expression-From-Speech.pdf)
- Morpheus (Zhang et al., RSS 2025, arXiv 2507.16645, Jul 2025): hybrid actuation, with rigid mechanisms for eyes and mouth and tendons for nose and cheeks. Speech → blendshape controls with emotion-specific signals (happiness, fear, disgust, anger). A self-model network (motor → landmarks) lets gradients backpropagate from blendshape targets to motor commands; the search summary reports 26 motors. Hardware and software are open. [PEER-REVIEWED] — [arXiv 2507.16645](https://arxiv.org/abs/2507.16645)
- SingingBot (Xu et al., arXiv 2601.02125, Jan 2026). [PREPRINT] — [arXiv 2601.02125](https://arxiv.org/html/2601.02125)
  - Pipeline: Hallo3 video diffusion (audio + portrait + text prompt) → 2D singing video → MediaPipe 52 ARKit coefficients → Gaussian smoothing → **hand-designed piecewise-linear map per blendshape to motor values, summed onto a rest pose** → 3 neck motors from head pose.
  - Animators set anchor pairs by posing actuators at chosen blendshape intensities. Shapes with no physical counterpart (cheekPuff) are zeroed, and asymmetric pairs on a shared actuator (noseSneerLeft/Right) are averaged.
  - Hardware: 32-DoF head (29 face + 3 neck). Generation runs on a remote A800; retargeting runs locally on an RK3588.
  - Results: user study (40 responses, 1–5 scale) gave realism 3.02, resonance 3.05, lip-sync 3.57, vs 1.94 / 1.73 / 2.21 for the next baseline. The authors argue emotional *range* (their EDR metric) matters beyond lip-sync accuracy. Replacing the generated avatar with EmoTalk-rendered animation degraded results.
- Zhang et al., "Automated Synthesis of Facial Mechanisms for Conversational Animatronic Robots", RSS 2026 (arXiv 2607.11688, Jul 2026). It generates a linkage mechanism from a portrait using AU-derived trajectory objectives, with a "dual-identity" speaking-and-listening motion synthesis from audio for physical execution. A listing summary says small per-region networks map blendshapes → actuators. No LLM is involved. [PREPRINT, accepted] — [arXiv 2607.11688](https://arxiv.org/abs/2607.11688); [alphaXiv](https://www.alphaxiv.org/abs/2607.11688)

### Inferences
- For Frank (hobby servos, about 16 channels), SingingBot's hand-tuned piecewise-linear "blendshape → servo" map is the realistic route. Learned inverse models (Emo, Morpheus) need camera self-modelling rigs and training. Using an ARKit-52-like intermediate would also let Frank be puppeteered from MediaPipe on the existing webcam for testing and authoring.
- Audio2Face's `preferred_emotion_strength` is the cleanest published precedent for Frank's split. The LLM tag acts as the "preferred emotion", a signal-level estimate from the actual TTS audio supplies "generated" emotion, and the engine blends them, then applies strength, contrast, smoothing and a max-emotions cap. Audio2Emotion itself is licence-restricted to the Audio2Face project, so a hobby engine would substitute simple audio features (RMS energy, pitch range) as an arousal proxy (inference; not tested in any source found).
- Audio2Photoreal's coarse-then-fine structure (1 fps guide poses + 30 fps detail) mirrors the LLM-tag (sparse, semantic) / engine (dense, dynamic) split.

### Gaps
- No source found that measures end-to-end latency of Audio2Face driving a *physical* animatronic, or anyone running A2F on servo heads.
- The licence terms for the Audio2Face-3D models' commercial use conflict between NVIDIA pages, and were not resolved.
- The full texts of Morpheus and the IROS 2024 paper (motor counts, control rates) were not read; only abstracts.

## 4. Emotion from text or voice as signals: Hume, text emotion classifiers on streamed text, ElevenLabs v3 audio tags; LLM tagging vs inference

### Takeaway
Three signal sources exist: (a) the LLM tags its own text, (b) a classifier reads the streamed text, (c) a model reads the audio prosody. Vendors expose all three, with explicit trade-offs. Convai's docs name the text-classifier path "Responsive" (streams, changes mid-reply) and the LLM path "Accurate" (reads the finished reply, later). For Frank, the TTS audio is generated *from* the tags, so the tag is the cause and audio inference is a check. The best documented pattern is to blend both (NVIDIA A2F), not to pick one. Hume's 48-dimension prosody API was sunset in mid-2026 and replaced by a limited-release product, so building on it is risky.

### Cited Findings
- ElevenLabs Eleven v3 audio tags. [VENDOR DOCS] — [ElevenLabs prompting guide](https://elevenlabs.io/docs/best-practices/prompting); [ElevenLabs help: audio tags](https://help.elevenlabs.io/hc/en-us/articles/35869142561297-How-do-audio-tags-work-with-Eleven-v3); [ElevenLabs blog: v3 audio tags](https://elevenlabs.io/blog/v3-audiotags)
  - Emotion and delivery tags include [excited], [sighs], [sarcastic], [curious], [whispers] and [laughs]; ellipses add pauses and capitals add emphasis.
  - "Voice choice is the most important parameter". A tag that clashes with the voice "likely won't work well", and some experimental tags are less consistent across voices.
  - Expressive tags work best with the "Creative" or "Natural" stability settings; "Robust" reduces responsiveness to direction.
- ElevenLabs latency: "there is no way to get Eleven v3 quality at Flash speeds". Flash's ~75 ms is model inference only (internal measurement, excluding network). Streaming "does not reduce model inference latency, but it dramatically reduces perceived latency". [VENDOR DOCS] — [ElevenLabs: Understanding latency](https://elevenlabs.io/docs/eleven-api/concepts/latency)
- A third-party review states that ElevenLabs says v3 has higher latency and "is not suitable for real-time or conversational use cases". This is from a competitor (Inworld), so check it. [SECONDARY] — [Inworld: ElevenLabs v3 review](https://inworld.ai/resources/elevenlabs-v3-review); Deepgram estimates 125–225 ms real-world for Flash — [Deepgram](https://deepgram.com/learn/is-elevenlabs-real-time-what-developers-need-to-know)
- Hume. [VENDOR DOCS; dates conflict as noted]
  - The legacy speech-prosody model measured 48 expression dimensions from "how something is said rather than what is said". Scores are "the likelihood that an average human perceiver would use that emotion dimension to describe a given expression", with time-interval output. — [Hume prosody docs (search snippet)](https://dev.hume.ai/docs/expression-measurement/models/prosody); [Hume science](https://dev.hume.ai/docs/resources/science)
  - A sunset notice: May 14, 2026 was the last day to create new jobs through the Playground and June 14, 2026 the last day to use the API. — [Hume Expression Measurement docs (search snippet)](https://dev.hume.ai/docs/expression-measurement/faq)
  - The current overview page (fetched 2026-10-30) instead describes a "limited release" API: per speech window, audio scores for up to 415 expression names and 190 voice-attribute names, plus video scores for 48 expressions. The 20 Oct 2026 changelog added "neutral" (415 names) for "audio upload and audio realtime". — [Hume EM overview](https://dev.hume.ai/docs/expression-measurement/overview); [Hume changelog 2026-10-20](https://dev.hume.ai/expression-measurement/changelog/2026/10/20.md)
  - A third-party page claims EVI access ends Nov 13, 2026. It could not be verified (page 404) and is unconfirmed. — [developersdigest (unverified)](https://www.developersdigest.tech/voice-agents/hume-evi)
- Convai's emotion system, on how the label is produced. [VENDOR DOCS] — [Convai: How the emotion system works](https://docs.convai.com/api-docs/plugins-and-integrations/convai-unity-sdk/features/emotion/how-the-emotion-system-works)
  - `EmotionDetectionMode.Nrclex` (default, "Responsive") reads the reply *as it streams*, so the face can change more than once per reply.
  - `EmotionDetectionMode.Llm` ("Accurate") reads the *finished* reply once, later, weighing meaning over wording; recommended for non-English.
  - `Off` requests no signal.
  - NRCLex is, by name, the NRC emotion-lexicon approach; the page does not state this.

### Inferences
- For Frank, the LLM's own inline tag is the lowest-latency, most coherent source. It arrives in the text stream *before* the audio for that phrase, costs a few tokens, and is the same token that steers ElevenLabs delivery, so face and voice share a cause. A post-hoc classifier (Convai "Accurate" style) adds a call and arrives late. A lexicon classifier is fast but shallow.
- Inference from audio should therefore be a *modulator*, not the selector: measured loudness and pitch movement of the actual v3 audio (local, near-zero latency) scale arousal and intensity. That catches cases where v3 under-delivers or ignores a tag (ElevenLabs warns tags can clash with a voice), so the face doesn't overshoot a flat voice.
- Hume's churn (sunset, then a new limited release) argues against depending on a cloud emotion-measurement API in the loop, for both latency and continuity.
- The user's (not Frank's) emotional state from the webcam or voice is a separate input that the LLM can reason about (Mishra et al.'s appraisal-per-turn approach), not something to mirror directly at the motor level. Emo-style mirroring is an engine-level reflex option, not an LLM decision.

### Gaps
- Not verified whether Eleven v3's streaming endpoints return character- or word-level timestamps/alignment usable for scheduling face events, or whether tags are stripped from the alignment.
- No published latency for v3 time-to-first-byte.
- No head-to-head study found of self-tagging vs classifier tagging for robot faces.

## 5. Commercial character platforms (Disney, Moxie, Furhat, Sophia, Inworld, Convai, NVIDIA ACE): connecting LLM output to animation, emotion-state APIs with intensity

### Takeaway
The most detailed public emotion-to-face architecture is Convai's Unity SDK. It has two channels (a persistent *mood* baseline and a *transient* reaction that rises, decays and settles back to mood), an optional micro-burst on onset, blending with complementary emotions, valence/arousal/agency/approach dimensions in [-1, 1] for gaze and body, and a facial compositor in which lip-sync wins mouth shapes during speech. NVIDIA ACE/Audio2Face offers the parallel audio-side pattern. Inworld exposes simple per-emotion morph-target weights. No Disney LLM-driven animatronic work was found.

### Cited Findings
- Convai. [VENDOR DOCS] — [Convai: How the emotion system works](https://docs.convai.com/api-docs/plugins-and-integrations/convai-unity-sdk/features/emotion/how-the-emotion-system-works); [Convai: emotion output bindings](https://docs.convai.com/api-docs/plugins-and-integrations/unity-plugin-beta-overview/features/emotion/output-bindings)
  - Labels resolve through an `EmotionTaxonomyAsset` (default Plutchik, 9 emotions incl. neutral). "An unresolved label logs one warning and falls back to neutral."
  - Transient channel (`CurrentResolvedEmotion`, `CurrentNormalizedIntensity`) "rises and decays with each signal, then settles toward the mood". Mood channel (`CurrentMoodLabel`, `CurrentMoodScore`) is set by the personality baseline or `SetMood` and persists; "Reactions never overwrite it".
  - Optional micro-burst: "a short overshoot on arrival".
  - A primary emotion can show alongside taxonomy complements (e.g. joy with trust).
  - `EmotionDimensions` (Valence, Arousal, Agency, Approach), clamped to [-1, 1], are read by the Gaze and Body modules.
  - Emotion submits to a shared facial compositor instead of writing blendshapes. The compositor "resolves overlapping claims on the mouth during speech", and a micro-expression layer adds idle drift and speech-emphasis accents. Semantic names (e.g. `MouthSmileLeft`) resolve to ARKit, CC3/CC4 or MetaHuman rigs.
  - Dialogue reactions (Listening, Thinking, Reacting Accent, Interrupted Flinch) default to strength 0.
  - Search snippets of Convai docs describe the server emotion intensity on a 1–3 scale normalised to 0–1 and fed to an accumulator with exponential smoothing. That was not confirmed on the fetched page, and numeric constants are not published there.
- Inworld (Unity SDK reference): each emotion maps to a list of "morph states" (morph target → weight). No intensity or lip-sync interplay was confirmed. [VENDOR DOCS] — [Inworld: InworldFacialEmotion](https://docs.inworld.ai/docs/tutorial-integrations/Unity/package-resources/api-references/inworld-assets/Animation/Facial/InworldFacialEmotion)
- NVIDIA ACE / Audio2Face: see section 3. Audio-inferred emotion is blended with an app-supplied "preferred emotion" at `preferred_emotion_strength` (default 0.5), with strength, contrast, smoothing and max-emotions controls. — [NVIDIA A2F parameter tuning](https://docs.nvidia.com/ace/latest/modules/a2f-docs/text/param_tuning.html)
- Furhat: FurhatAI Creator advertises "Expressivity Controls" with Azure OpenAI 4o-mini. The research systems above (Mishra 2023, FurChat 2023, Galatolo 2025, Abbo 2025) show LLM label → Furhat gesture mapping. [VENDOR DOCS / PEER-REVIEWED] — [FurhatAI Creator](https://www.furhatrobotics.com/de/furhat-creator)
- Disney: no LLM-driven Disney animatronic face work found. [MARKETING/PRESS]
  - Nov 2025: Walt Disney Imagineering showed a static facial shell given micro-expressions by real-time projection. — [AV Interactive](https://www.avinteractive.com/markets-news/visitor-attractions/how-disneys-projectors-bring-emotion-to-animatronic-faces-27-11-2025/)
  - Sept 2025: patent application US18/592,863 on projection onto moving animatronic surfaces. — [WDWMagic](https://www.wdwmagic.com/other/walt-disney-imagineering/news/12sep2025-disney-patent-targets-real-time-projection-on-animatronic-faces.htm)
  - 2020: Disney Research's gaze system for an Audio-Animatronic layered breathing and blinking onto attention behaviours (pre-LLM). — [Impact Lab](https://www.impactlab.com/2020/11/15/disneys-robot-can-perform-realistic-eye-movements-social-interaction/)

### Inferences
- Convai's mood/transient split is a ready-made answer to "emotion as a continuous spectrum". Frank's LLM tags drive transient reactions with attack, overshoot, decay and settle. A slower mood state, nudged by repeated tags or set per scene, provides the baseline the face returns to. This also prevents flip-flopping, because a single stray tag only produces a transient that decays.
- Mapping each of Frank's 10 tags to a point in VA (plus agency/approach) space gives a continuous space for interpolation and a cheap signal for gaze (e.g. irritated → more direct gaze, vulnerable → more gaze aversion). This is a design inference from Convai's dimension outputs; no source evaluated it on a robot.
- "Unresolved label → neutral with a warning" is the right failure policy for a streaming tag parser.

### Gaps
- No public technical details found for Moxie (Embodied; the company wound down in late 2024, not re-verified here), Hanson's Sophia LLM pipeline, NVIDIA ACE Tokkio's LLM → emotion wiring, or Disney's interactive characters with LLMs.
- Convai's numeric smoothing constants and update rates are unpublished on the pages read.

## 6. Reported failure modes: over-expressiveness, flip-flopping, word–face mismatch, tag-to-face latency, uncanny valley

### Takeaway
The best-documented failures are *incongruence* (face contradicts words or context, which makes users doubt themselves) and *mistiming* (expression after speech, or gaze toward the wrong person). Latency across the whole chain (ASR + LLM + TTS) is the dominant engineering constraint and drove model choice at Engineered Arts. No study isolates over-expressiveness or emotion flip-flopping as a variable; those risks are addressed in vendor designs (smoothing, mood baselines, caps) rather than measured in papers.

### Cited Findings
- Mistiming: on Ameca, expressions shown only after lip-synced speech were judged "not correctly timed; they didn't feel authentic". The authors call simultaneous expression and lip-sync a key requirement. [PEER-REVIEWED] — [Kirjavainen et al., Mindtrek '25](https://lacris.ulapland.fi/ws/files/46321884/3757980.3757996.pdf)
- Incongruence: inappropriate expressions caused confusion and self-doubt (P28: "made me think I'd asked a bad question"), and appropriate ones improved pragmatic UX. Some participants still found incongruent faces engaging, "funny" or "like art". [PEER-REVIEWED] — [Mindtrek '25](https://lacris.ulapland.fi/ws/files/46321884/3757980.3757996.pdf); in Mishra et al., congruent LLM-chosen expressions were rated more human-like than incongruent ones — [PMC10722897](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10722897/)
- Odd combinations: LLM-tagged Furhat behaviour sometimes produced "smiling while talking" combinations judged odd. [PEER-REVIEWED] — [Galatolo & Winkle 2025](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1581024/full)
- Invalid output: small LLMs emitted invalid gesture tags 27–62% of the time with prompt-only tagging; a 70B model 2–3%. [PEER-REVIEWED] — [Galatolo & Winkle 2025](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1581024/full)
- Inconsistent behaviour: GenEM reused learned skills inconsistently and called undefined functions when capabilities were removed. [PEER-REVIEWED] — [GenEM arXiv HTML](https://arxiv.org/html/2401.14673v2)
- Gaze–speech mismatch: the robot looking at one person while replying to another confused participants. [PREPRINT] — [Abbo et al. 2025](https://arxiv.org/html/2503.15496v2)
- Latency:
  - GPT-4 made Ameca "appear less responsive", so GPT-3 was used. [first-party] — [Ameca on X](https://x.com/AmecaTheRobot/status/1641749840580280321)
  - The Furhat multi-party system averaged 1.35 s response delay (SD 0.55, up to about 5 s), with the LLM taking 0.76 s on average. [PREPRINT] — [Abbo et al. 2025](https://arxiv.org/html/2503.15496v2)
  - Inline tags with in-context learning cost 3.3× generation time on local small models. [PEER-REVIEWED] — [Galatolo & Winkle 2025](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1581024/full)
- Jitter vs freezing: Audio2Face documents a smoothing parameter from 0, "can be jittery", to 1, "emotion values not updated over time". [VENDOR DOCS] — [NVIDIA A2F param tuning 1.0](https://docs.nvidia.com/ace/audio2face-3d-microservice/1.0/text/param-tuning.html)
- Uncanny valley:
  - A 2025 *Frontiers in Psychology* paper on embodied conversational agents reports strong empirical support for the perceptual-mismatch hypothesis. [PEER-REVIEWED] — [Frontiers in Psychology 2025](https://public-pages-files-2025.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1625984/pdf)
  - A 2025 review argues the effect is heightened when near-human appearance lacks natural emotional expression or movement. [PEER-REVIEWED] — [Frontiers in Psychology](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1569277/full)
  - In a multi-session LLM-powered robot study with students, observers logged expressions unrelated to the conversation, with "no habituation effect in reducing perceptions of creepiness or uncanny feelings" over sessions. [PEER-REVIEWED] — [PMC12170534](https://pmc.ncbi.nlm.nih.gov/articles/PMC12170534/)
- Physical damping: Ameca expressions rendered less pronounced on the physical face than in preview. [PEER-REVIEWED] — [Mindtrek '25](https://lacris.ulapland.fi/ws/files/46321884/3757980.3757996.pdf)

### Inferences
- The tag → face latency problem in Frank is solvable locally. Because tags arrive in the text stream ahead of the audio they belong to, the engine can schedule the expression onset against audio playback time, starting slightly before the tagged phrase (anticipatory onset, cf. Emo's predictive co-expression), not at tag-parse time or after the line.
- Flip-flopping protection belongs entirely in the engine: minimum dwell time per transient, hysteresis on mood changes, decay toward mood rather than snapping to neutral, and an intensity ceiling (A2F-style strength and contrast) tuned so the face doesn't over-perform a flat voice.
- "Expressions unrelated to the conversation" arises when idle or random behaviour is too strong. Idle micro-motion (blinks, saccades, breathing) should be low-amplitude and subordinate to the current emotion state.

### Gaps
- No controlled study found on over-expression intensity or emotion-switch rate in LLM-driven robot faces.
- No measured tag-to-face latency numbers from any commercial platform.

## 7. Synthesis: what the 2023–2026 evidence says about the split between what the LLM decides and what the engine decides

### Takeaway
Every system with published detail puts the LLM at the *semantic, sparse, per-phrase* level: which emotion or skill, roughly how strong, where in the utterance. The *continuous, dense, per-frame* level goes to deterministic or learned local layers: timing against audio, onset/overshoot/decay, mood baseline, blending, smoothing, lip-sync arbitration on the mouth, gaze from perception, idle motion and actuator mapping. Asking the LLM for numbers or low-level motion is slower and less reliable, and no source shows it working better.

### Cited Findings
- The LLM does social reasoning; execution is limited to predefined skills (GenEM). — [CACM](https://cacm.acm.org/news/teaching-robots-manners); [arXiv 2401.14673](https://arxiv.org/html/2401.14673v2)
- Inline label + intensity tags are the established cheap format; prompt-only tagging needs validation, and a constrained vocabulary helps. — [Galatolo & Winkle 2025](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2025.1581024/full)
- LLMs are weak at mapping VA numbers to categories, so labels are the safer interface. — [Mehra, Laban, Gunes 2025](https://dl.acm.org/doi/10.1145/3719160.3737618)
- Label + intensity → normalise → transient channel over a persistent mood → compositor with lip-sync priority on the mouth → VA dimensions shared with gaze and body (Convai). — [Convai docs](https://docs.convai.com/api-docs/plugins-and-integrations/convai-unity-sdk/features/emotion/how-the-emotion-system-works)
- Externally chosen ("preferred") emotion blended with audio-inferred emotion, plus strength, contrast, smoothing and max-emotions (NVIDIA A2F). — [NVIDIA A2F config](https://docs.nvidia.com/ace/audio2face-3d-microservice/1.3/text/deployment/container-config.html)
- Gaze and turn-taking are driven by perception, not the LLM; a brow-raise acknowledgement plays on transcription (Abbo et al.). — [arXiv 2503.15496](https://arxiv.org/html/2503.15496v2)
- Lip-sync and motor realism come from signal-level models (Emo 2026 lip-sync; IROS 2024; Morpheus; SingingBot), with ARKit-52 as the shared space and hand-tuned piecewise-linear maps viable for low-DoF heads. — [TechXplore](https://techxplore.com/news/2026-01-robot-lip-sync-youtube.html); [arXiv 2403.12670](https://arxiv.org/abs/2403.12670); [arXiv 2507.16645](https://arxiv.org/abs/2507.16645); [arXiv 2601.02125](https://arxiv.org/html/2601.02125)
- Latency drove model choice on Ameca (GPT-3 over GPT-4). — [Ameca on X](https://x.com/AmecaTheRobot/status/1641749840580280321)

### Inferences
These are concrete lessons for Frank's Python engine (cloud Sonnet + ElevenLabs v3 + local servos at 25–50 Hz). They are inferences from the sources above and have not been tested.
1. **LLM decides:** the emotion label from the closed set of 10, optional coarse intensity (e.g. 1–3, as in Galatolo's tag parameter and Convai's server scale), and placement in the text. It may also set a scene-level mood. It should not output angles, VA floats or timing.
2. **Engine decides:**
   - each tag's onset time against audio playback, with a small lead;
   - the transient envelope (attack, overshoot "micro-burst", hold, decay toward mood);
   - mood drift with hysteresis and dwell time;
   - continuous blending in a VA (+ agency) space or per-actuator pose space;
   - arousal modulation from the actual TTS audio envelope and pitch;
   - mouth arbitration (jaw and lips from audio take priority during speech; emotion offsets the corners within clamps);
   - brows, lids and eyes carrying emotion during speech;
   - gaze from the webcam (speaker, targets), biased by emotion;
   - listening and "thinking" faces during the ~1.5 s gap before first sound;
   - idle blinks and breathing;
   - all servo limits.
3. **Parser policy:** a closed vocabulary, unknown tag → neutral plus a log entry, strip tags from any text shown to people, and never block audio on face processing.
4. **Avoid** a second LLM call to classify emotion (adds latency, arrives late) and cloud emotion APIs in the loop (Hume's 2026 sunset and churn). Use local audio features as a modulator.
5. **Authoring:** use a SingingBot-style per-pose, per-servo piecewise-linear table, tuned on the physical head (Ameca's physical damping lesson). Optionally use MediaPipe ARKit-52 from the webcam as a puppeteering and authoring source.
6. **Test against the documented failures:**
   - expression only after speech;
   - face contradicting words;
   - gaze at the wrong person;
   - jitter vs frozen face (the smoothing extremes);
   - idle motion that reads as unrelated to the conversation.

### Gaps
- No source measures any of these engine-side choices (lead time, decay constants, dwell times) on a physical face. They need bench tuning on Frank.
- Whether ElevenLabs v3 streaming exposes alignment timestamps (needed to place tag onsets precisely) was not confirmed. Without it, the engine has to estimate phrase timing from audio chunk arrival and playback position.
