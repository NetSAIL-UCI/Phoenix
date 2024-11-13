# from . import ROOT_PATH
import os
import random

current_directory = os.getcwd()

words_dir = current_directory + "/src/workloads/cloudlab/loadgen/loadgenerator/"
with open(os.path.join(words_dir, "words"), "r") as f:
    WORDS = map(lambda s: s.strip(), f.readlines())

def sample(minimum, maximum):
    if maximum == minimum:
        maximum = minimum+1
    return random.sample(list(WORDS), random.randint(minimum, maximum))
