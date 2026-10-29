"""
Splits Frank's streamed reply into face commands and sentences for the voice.

The model writes expression tags in square brackets inside its text ([curious],
[chuckle], ...; frank/README.md, "Expression tags"). Feed the text deltas in as they
arrive. Each feed() returns the events that are complete so far, in order:
    ("face", "curious")      set the expression now
    ("sound", "chuckle")     play the chuckle
    ("say", "Oh! Really?")   a whole sentence, ready for the voice
A tag in the middle of a sentence comes out before that sentence, so the face changes
as the sentence starts. Common stand-ins ([puzzled], [sceptical]) map to the nearest tag
(ALIASES). Other bracketed words are dropped (and listed in .unknown), never spoken.
"""

import re

FACES = ("neutral", "curious", "excited", "skeptical", "amused",
         "concentrating", "confused", "irritated", "surprised", "vulnerable")
SOUNDS = ("chuckle",)
# Words the models use instead of the real tags (seen in the 2026-10-26 bake-off and
# near misses), mapped to the closest face rather than dropped.
ALIASES = {
    "sceptical": "skeptical", "doubtful": "skeptical",
    "puzzled": "confused", "perplexed": "confused", "uncertain": "confused",
    "thoughtful": "concentrating", "pensive": "concentrating", "thinking": "concentrating",
    "serious": "neutral", "calm": "neutral", "dry": "neutral", "dryly": "neutral", "drily": "neutral",
    "concerned": "vulnerable", "worried": "vulnerable", "sad": "vulnerable", "gentle": "vulnerable",
    "intrigued": "curious", "interested": "curious", "fascinated": "excited", "delighted": "excited",
    "wry": "amused", "smiling": "amused", "bemused": "amused",
    "annoyed": "irritated", "shocked": "surprised", "startled": "surprised",
    "laugh": "chuckle", "laughs": "chuckle", "chuckles": "chuckle",
}

# Sentence end: . ! ? or … (repeats allowed), optional closing quote or bracket, then whitespace.
SENTENCE_END = re.compile(r"[.!?…]+[\"')\]]*\s+")
# A full stop after these doesn't end a sentence ("Mr. Holmes").
ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "st", "mt", "vs", "etc", "e.g", "i.e", "no"}
MAX_TAG = 40  # a "[" with no "]" within this many characters is not a tag


class TagStream:
    def __init__(self):
        self.buf = ""      # raw text not yet parsed (may end partway through a tag)
        self.speech = ""   # speakable text not yet a whole sentence
        self.unknown = []  # bracketed words that weren't tags

    def feed(self, delta):
        self.buf += delta
        out = []
        while self.buf:
            i = self.buf.find("[")
            if i < 0:
                self.speech += self.buf
                self.buf = ""
                break
            self.speech += self.buf[:i]
            self.buf = self.buf[i:]
            j = self.buf.find("]")
            if j < 0:
                if len(self.buf) > MAX_TAG:  # stray bracket: keep the text, lose the "["
                    self.speech += self.buf[1:]
                    self.buf = ""
                break  # wait for the rest of the tag
            word = self.buf[1:j].strip().lower()
            word = ALIASES.get(word, word)
            self.buf = self.buf[j + 1:]
            out += self._sentences()
            if word in FACES:
                out.append(("face", word))
            elif word in SOUNDS:
                out.append(("sound", word))
            else:
                self.unknown.append(word)
        return out + self._sentences()

    def flush(self):
        """End of the reply: whatever is left is the last sentence."""
        out = self.feed("")
        rest = self.speech.strip()  # self.buf can only hold an unfinished tag: drop it
        self.speech = self.buf = ""
        if any(c.isalnum() for c in rest):
            out.append(("say", _tidy(rest)))
        return out

    def _sentences(self):
        out = []
        start = 0
        while True:
            m = SENTENCE_END.search(self.speech, start)
            if not m:
                return out
            last_word = self.speech[:m.start()].split()[-1:] or [""]
            if self.speech[m.start()] == "." and last_word[0].lower() in ABBREVIATIONS:
                start = m.end()
                continue
            sentence = self.speech[:m.end()].strip()
            self.speech = self.speech[m.end():]
            start = 0
            if any(c.isalnum() for c in sentence):
                out.append(("say", _tidy(sentence)))


def _tidy(s):
    s = re.sub(r"[*#`_]", "", s)  # stray markdown would be read out by the voice
    return re.sub(r"\s{2,}", " ", s)


def parse(text):
    """Every event of a whole reply at once (for tests and logs)."""
    t = TagStream()
    return t.feed(text) + t.flush()
