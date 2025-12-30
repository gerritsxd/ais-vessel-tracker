import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm
import numpy as np
import re

# =========================================================
# 1. LOAD DATA
# =========================================================

df = pd.read_csv("nlp_filtered_chunks.csv")
df['chunk_text'] = df['chunk_text'].fillna("").astype(str)

print(f"Loaded {len(df)} text chunks for FinBERT sentiment.\n")

# =========================================================
# 2. LOAD FINBERT MODEL (finance sentiment)
# =========================================================

MODEL_NAME = "ProsusAI/finbert"

print("Loading FinBERT model...\n")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

print(f"Using device: {device}\n")

# =========================================================
# 3. HELPER FUNCTIONS
# =========================================================

def get_finbert_sentiment(text):
    """Return FinBERT positive, negative, neutral probabilities and compound score."""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits.detach().cpu().numpy()[0]

    probs = torch.softmax(torch.tensor(logits), dim=0).numpy()
    positive, negative, neutral = probs[0], probs[1], probs[2]

    compound = positive - negative
    return positive, negative, neutral, compound


def filter_sentences(text, keywords):
    """Return list of sentences containing any keyword."""
    sentences = re.split(r'[.!?]', text)
    return [s.strip() for s in sentences if any(kw in s.lower() for kw in keywords)]


def targeted_finbert_sentiment(text, keywords):
    """Apply FinBERT to only sentences containing specific keywords."""
    sents = filter_sentences(text, keywords)
    if not sents:
        return 0, 0, 0, 0  # no signal → neutral

    pos_list, neg_list, neu_list, comp_list = [], [], [], []

    for s in sents:
        p, n, u, c = get_finbert_sentiment(s)
        pos_list.append(p)
        neg_list.append(n)
        neu_list.append(u)
        comp_list.append(c)

    return (
        float(np.mean(pos_list)),
        float(np.mean(neg_list)),
        float(np.mean(neu_list)),
        float(np.mean(comp_list)),
    )

# =========================================================
# 4. KEYWORD GROUPS
# =========================================================

SUSTAINABILITY = ["sustainab", "green", "decarbon", "carbon", "net zero", "esg"]
INNOVATION = ["innov", "digital", "technology", "pilot", "research", "r&d"]
COST = ["cost", "expense", "budget", "profit", "economic", "savings"]
RISK = ["risk", "uncertain", "challenge", "barrier", "safety"]

# =========================================================
# 5. RUN FINBERT WITH PROGRESS BAR
# =========================================================

overall_pos, overall_neg, overall_neu, overall_comp = [], [], [], []
sust_comp, innov_comp, cost_comp, risk_comp = [], [], [], []

print("\nRunning FinBERT sentiment analysis...\n")

for text in tqdm(df["chunk_text"], desc="FinBERT Progress"):

    # --- Overall sentiment ---
    pos, neg, neu, comp = get_finbert_sentiment(text)
    overall_pos.append(pos)
    overall_neg.append(neg)
    overall_neu.append(neu)
    overall_comp.append(comp)

    # --- Targeted sentiments ---
    _, _, _, sust = targeted_finbert_sentiment(text, SUSTAINABILITY)
    _, _, _, innov = targeted_finbert_sentiment(text, INNOVATION)
    _, _, _, costv = targeted_finbert_sentiment(text, COST)
    _, _, _, riskv = targeted_finbert_sentiment(text, RISK)

    sust_comp.append(sust)
    innov_comp.append(innov)
    cost_comp.append(costv)
    risk_comp.append(riskv)

# =========================================================
# 6. SAVE RESULTS
# =========================================================

df["finbert_pos"] = overall_pos
df["finbert_neg"] = overall_neg
df["finbert_neu"] = overall_neu
df["finbert_compound"] = overall_comp

df["sentiment_sustainability"] = sust_comp
df["sentiment_innovation"] = innov_comp
df["sentiment_cost"] = cost_comp
df["sentiment_risk"] = risk_comp

df.to_csv("nlp_with_finbert.csv", index=False)

print("\nFinBERT sentiment COMPLETE.")
print("Saved to nlp_with_finbert.csv\n")

# =========================================================
# 7. SUMMARY STATISTICS
# =========================================================

print("=== FINBERT SENTIMENT SUMMARY ===")
sent_cols = [
    "finbert_pos", "finbert_neg", "finbert_neu", "finbert_compound",
    "sentiment_sustainability", "sentiment_innovation",
    "sentiment_cost", "sentiment_risk"
]

print(df[sent_cols].describe())

print("\n=== TOP POSITIVE COMPANIES (overall) ===")
print(df[["company_name", "finbert_compound"]].sort_values(by="finbert_compound", ascending=False).head(10))

print("\n=== MOST NEGATIVE COMPANIES (overall) ===")
print(df[["company_name", "finbert_compound"]].sort_values(by="finbert_compound").head(10))
