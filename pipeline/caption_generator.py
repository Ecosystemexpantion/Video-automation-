import re


def split_into_captions(script_text: str, words_per_caption: int = 5) -> list[str]:
    words = script_text.split()
    captions = []
    for i in range(0, len(words), words_per_caption):
        chunk = " ".join(words[i:i + words_per_caption])
        captions.append(chunk)
    return captions


def estimate_timings(captions: list[str], total_duration: float) -> list[tuple[float, float, str]]:
    word_counts = [len(c.split()) for c in captions]
    total_words = sum(word_counts)

    timed = []
    current_time = 0.0
    for caption, wc in zip(captions, word_counts):
        duration = (wc / total_words) * total_duration
        timed.append((current_time, current_time + duration, caption))
        current_time += duration

    return timed
