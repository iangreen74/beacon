from enum import Enum


class MoodEnum(str, Enum):
    great = "great"
    good = "good"
    okay = "okay"
    bad = "bad"
    terrible = "terrible"
