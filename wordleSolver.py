import streamlit as st
import requests
from collections import Counter, defaultdict

st.set_page_config(page_title="Wordle Solver", layout="centered")
st.title("Wordle Solver")

@st.cache_data
def load_word_list():
    url = "https://raw.githubusercontent.com/tabatkins/wordle-list/main/words"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return [w.strip().lower() for w in r.text.splitlines() if len(w.strip()) == 5]

WORD_LIST = load_word_list()
st.caption(f"Loaded {len(WORD_LIST)} official Wordle answer words")

if "colors" not in st.session_state:
    st.session_state.colors = [["gray"] * 5 for _ in range(6)]
if "words" not in st.session_state:
    st.session_state.words = [""] * 6

color_order = ["gray", "yellow", "green"]
emoji_for = {"gray": "⬜", "yellow": "🟨", "green": "🟩"}

def cycle_color(r, c):
    cur = st.session_state.colors[r][c]
    st.session_state.colors[r][c] = color_order[(color_order.index(cur) + 1) % len(color_order)]

def candidate_matches_guess(candidate: str, guess: str, colors: list) -> bool:

    candidate = candidate.lower()
    guess = guess.lower()
    for i, (gch, col) in enumerate(zip(guess, colors)):
        if col == "green":
            if candidate[i] != gch:
                return False
        elif col == "yellow":
            if candidate[i] == gch:
                return False 
    non_gray_counts = Counter()
    total_counts_in_guess = Counter()
    for gch, col in zip(guess, colors):
        total_counts_in_guess[gch] += 1
        if col != "gray":
            non_gray_counts[gch] += 1
    candidate_counts = Counter(candidate)

    for letter, tot in total_counts_in_guess.items():
        req_non_gray = non_gray_counts.get(letter, 0)
        if req_non_gray == 0:
            if candidate_counts.get(letter, 0) != 0:
                return False
        elif tot > req_non_gray:
            if candidate_counts.get(letter, 0) != req_non_gray:
                return False
        else:
            if candidate_counts.get(letter, 0) < req_non_gray:
                return False

    for i, (gch, col) in enumerate(zip(guess, colors)):
        if col == "yellow":
            if candidate_counts.get(gch, 0) == 0:
                return False

    return True

def filter_candidates(all_words, guesses):
    results = []
    for w in all_words:
        ok = True
        for g in guesses:
            if not candidate_matches_guess(w, g["guess"], g["colors"]):
                ok = False
                break
        if ok:
            results.append(w)
    return results

st.markdown("---")
for r in range(6):
    cols = st.columns([1, 1, 1, 1, 1, 0.5])  
    letters = list(st.session_state.words[r])
    while len(letters) < 5:
        letters.append("")

    new_word = ""
    for c in range(5):
        with cols[c]:
            val = st.text_input(
                label="", 
                value=letters[c].upper(),
                max_chars=1,
                key=f"letter_{r}_{c}",
                label_visibility="collapsed"
            )
            new_word += val.lower() if val else ""
            if st.button(emoji_for[st.session_state.colors[r][c]], key=f"color_{r}_{c}"):
                cycle_color(r, c)
                st.rerun()

    st.session_state.words[r] = new_word

st.markdown("---")

if st.button("Get Next Possible Words (and Best)"):
    guesses = []
    for r in range(6):
        g = st.session_state.words[r]
        if len(g) == 5 and g.isalpha():
            guesses.append({"guess": g.lower(), "colors": st.session_state.colors[r]})

    if not guesses:
        st.warning("No valid guesses entered yet.")
    else:
        candidates = filter_candidates(WORD_LIST, guesses)

        if not candidates:
            st.warning("No possible words found with current constraints.")
        else:
            freq = Counter()
            for w in candidates:
                freq.update(list(dict.fromkeys(w)))
            scored = []
            for w in candidates:
                unique_letters = list(dict.fromkeys(w))
                score = sum(freq[ch] for ch in unique_letters)
                scored.append((score, w))
            scored.sort(reverse=True)  

            best_score, best_word = scored[0]
            st.success(f"Best suggestion: {best_word.upper()} (score {best_score})")
            st.write(f"Top {min(50, len(scored))} suggestions (ranked):")
            st.write(", ".join(w.upper() for _, w in scored[:50]))
            st.caption(f"({len(candidates)} total matches)")


# --- New: Suggest Maximizing Word (for info gain) ---
if st.button("Get Maximizing Word (Use New Letters)"):
    guesses = []
    for r in range(6):
        g = st.session_state.words[r]
        if len(g) == 5 and g.isalpha():
            guesses.append({"guess": g.lower(), "colors": st.session_state.colors[r]})

    if not guesses:
        st.warning("Please enter at least one guess first.")
    else:
        candidates = filter_candidates(WORD_LIST, guesses)
        guessed_letters = set("".join(g["guess"] for g in guesses))

        # Score words that introduce the most *new* letters not guessed yet
        scored = []
        for w in WORD_LIST:
            unique_letters = set(w)
            # prefer words with 5 unique letters
            diversity_bonus = len(unique_letters)
            # new letters not yet guessed
            new_letters = len(unique_letters - guessed_letters)
            # combine score
            score = new_letters * 2 + diversity_bonus
            scored.append((score, w))

        scored.sort(reverse=True)
        best_score, best_word = scored[0]
        st.success(f"Try this word for maximum information: {best_word.upper()} (score {best_score})")
        st.write(f"Top 20 info-gain words: {', '.join(w.upper() for _, w in scored[:20])}")


if st.button("Reset"):
    st.session_state.colors = [["gray"] * 5 for _ in range(6)]
    st.session_state.words = [""] * 6
    st.rerun()
