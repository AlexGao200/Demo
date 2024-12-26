import re


def remove_non_latin_chars(text):
    # Remove repetitive characters (like dots in table of contents)
    text = re.sub(r"[\.]{2,}", ".", text)
    text = re.sub(r"[\s]{2,}", " ", text)

    # Remove non-extended Latin alphabet/number/punctuation characters
    text = re.sub(r"[^\x00-\x7F]+", "", text)

    # Optional: Remove extra whitespace
    text = " ".join(text.split())

    return text


def remove_whitespace_and_returns(text):
    return text.replace("\n\n", "\n").replace("\n", " ").replace("\t", " ").strip()
