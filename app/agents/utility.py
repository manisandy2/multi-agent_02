from typing import Any, Dict

EMOTION_KEYWORDS = {
    "joy": ["happy", "excellent", "great", "good", "love", "delighted", "pleased", "awesome", "thanks", "thank"],
    "sadness": ["sad", "disappointed", "unhappy", "sorrow", "regret"],
    "anger": ["angry", "hate", "furious", "annoyed", "terrible", "worst"],
}

ATTRIBUTE_KEYWORDS = {
    "product": ["product", "device", "phone", "model", "item", "iphone", "samsung", "mobile"],
    "service": ["service", "support", "warranty", "repair", "assistance"],
    "delivery": ["delivery", "shipping", "courier", "arrival"],
    "pricing": ["price", "pricing", "cost", "expensive", "cheap", "emi"],
    "staff": ["staff", "salesperson", "manager", "employee"],
    "store experience": ["store", "showroom", "ambience", "queue", "waiting"],
}

def detect_attributes_and_emotion(text: str) -> Dict:
    text_l = (text or "").lower()
    if not text_l:
        return {"attributes": ["other"], "emotion": "other"}
    detected = set()
    for attr, kws in ATTRIBUTE_KEYWORDS.items():
        if any(kw in text_l for kw in kws):
            detected.add(attr)
    max_emo = None
    max_score = 0
    for emo, kws in EMOTION_KEYWORDS.items():
        score = sum(text_l.count(kw) for kw in kws)
        if score > max_score:
            max_score = score
            max_emo = emo
    return {"attributes": list(detected) if detected else ["other"], "emotion": max_emo if max_emo else "other"}

def call_gemini_sync(review_text: str, star_rating: int, customer_name: str, store_location: str) -> Dict:
    """Synchronous Gemini call with original prompt"""
    customer_name_norm = normalize_name(customer_name)
    store_canonical = _normalize_title(store_location)
    star_rating_int = parse_star_rating(star_rating, default=3)
    
    selected_tone = random.choice(REPLY_TONES)
    sentiment = "positive" if star_rating_int >= 4 else ("negative" if star_rating_int <= 2 else "neutral")
    
    if sentiment == "positive":
        example_opening = random.choice(POSITIVE_OPENINGS)
    elif sentiment == "negative":
        example_opening = random.choice(NEGATIVE_OPENINGS)
    else:
        example_opening = random.choice(NEUTRAL_OPENINGS)

    prompt = f"""You are a sentiment, emotion, and attribute analyzer for Poorvika, a leading electronics retailer.

                **TASK:**
                1. Analyze the customer review below
                2. Generate a personalized, high-quality reply

                **REVIEW DETAILS:**
                - Customer Name: {customer_name_norm or '<Name>'}
                - Star Rating: {star_rating_int}/5
                - Store Location: {store_canonical}
                - Review Text: "{review_text}"

                **ANALYSIS REQUIREMENTS:**
                1. **Sentiment**: Classify as positive, neutral, or negative
                2. **Emotion**: Identify primary emotion (joy, sadness, anger, fear, surprise, disgust, or other)
                3. **Attributes**: Identify all relevant categories:
                - product, service, delivery, pricing, staff, store experience, or other
                - Multiple attributes allowed

                **REPLY GENERATION RULES:**

                **Format (STRICTLY FOLLOW):**
                - Single paragraph, no "Dear" greeting prefix
                - Body (4-5 sentences, 60-80 words) - Be specific and natural
                - NO "Regards," or store name closing required
                - Reply should end naturally with forward-looking statement

                **Tone & Style:**
                - Use this style: {selected_tone}
                - Sound natural and conversational (NOT robotic or templated)
                - Personalize the response based on review content
                - Reference specific points from the review when relevant
                - Integrate store location naturally into the response

                **Content Guidelines:**
                - **Positive Reviews (4-5 stars):**
                * Start with: "Thank you so much for your wonderful {star_rating_int}-star review!"
                * Acknowledge specifically what they praised from the review
                * Express genuine gratitude and enthusiasm
                * Mention store location naturally
                * End with: "We look forward to welcoming you back soon!"
                * Example tone: "{example_opening}"

                - **Negative Reviews (1-2 stars):**
                * Start with sincere apology
                * Example: "{example_opening}"
                * Acknowledge their specific concern based on the context
                * MUST include: "Please contact us at {EMAIL}"
                * Show commitment to resolution

                - **Neutral Reviews (3 stars):**
                * Thank them professionally
                * Acknowledge feedback constructively
                * Show commitment to improvement

                **Quality Checklist:**
                ✓ Starts naturally without formal "Dear..." greeting
                ✓ Mentions specific star rating: {star_rating_int} stars
                ✓ Acknowledges what customer specifically mentioned
                ✓ Store location mentioned naturally in body
                ✓ Tone matches star rating
                ✓ 60-80 words (detailed and comprehensive)
                ✓ Natural language (not generic or templated)
                ✓ Specific to their review content
                ✓ No spelling/grammar errors
                ✓ NO formal closing (no "Regards," "Best wishes," "Sincerely," etc.)

                IMPORTANT: Respond with only the JSON object and nothing else. Do not add explanation or markdown formatting.

                **OUTPUT FORMAT (JSON only):**
                {{
                "sentiment": "<positive|neutral|negative>",
                "emotion": "<joy|sadness|anger|fear|surprise|disgust|other>",
                "attributes": ["<category1>", "<category2>"],
                "star_rating": {star_rating_int},
                "reply": "[Natural personalized response - single paragraph, 4-5 sentences, 60-80 words, no formal closing]"
                }}
                """

    config = types.GenerationConfig(temperature=0.3, top_p=0.95, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS)
    
    if not GENAI_API_KEY:
        heuristics = detect_attributes_and_emotion(review_text)
        return {
            "parsed": {
                "sentiment": sentiment,
                "emotion": heuristics["emotion"],
                "attributes": heuristics["attributes"],
                "star_rating": star_rating_int,
                "reply": build_reply_template(customer_name_norm, store_canonical, star_rating_int, sentiment),
            },
            "quality_score": 50
        }

    try:
        model = genai.GenerativeModel(model_name=MODEL)
        response = model.generate_content(prompt, generation_config=config)
        
        # Check for safety blocks or other issues
        if not response.candidates:
            logger.warning(f"No candidates returned (likely safety block)")
            heuristics = detect_attributes_and_emotion(review_text)
            return {
                "parsed": {
                    "sentiment": sentiment,
                    "emotion": heuristics["emotion"],
                    "attributes": heuristics["attributes"],
                    "star_rating": star_rating_int,
                    "reply": build_reply_template(customer_name_norm, store_canonical, star_rating_int, sentiment),
                },
                "quality_score": 50
            }
        
        # Check finish reason
        candidate = response.candidates[0]
        if hasattr(candidate, 'finish_reason'):
            # finish_reason: 0=STOP (success), 1=MAX_TOKENS, 2=SAFETY, 3=RECITATION, 4=OTHER
            if candidate.finish_reason == 2:  # SAFETY block
                logger.warning(f"Gemini safety block on review: {review_text[:100]}")
                heuristics = detect_attributes_and_emotion(review_text)
                return {
                    "parsed": {
                        "sentiment": sentiment,
                        "emotion": heuristics["emotion"],
                        "attributes": heuristics["attributes"],
                        "star_rating": star_rating_int,
                        "reply": build_reply_template(customer_name_norm, store_canonical, star_rating_int, sentiment),
                    },
                    "quality_score": 50
                }
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        heuristics = detect_attributes_and_emotion(review_text)
        return {
            "parsed": {
                "sentiment": sentiment,
                "emotion": heuristics["emotion"],
                "attributes": heuristics["attributes"],
                "star_rating": star_rating_int,
                "reply": build_reply_template(customer_name_norm, store_canonical, star_rating_int, sentiment),
            },
            "quality_score": 50
        }

    raw_text = ""
    if hasattr(response, 'text'):
        raw_text = response.text
    elif hasattr(response, 'candidates') and response.candidates:
        for cand in response.candidates:
            content = getattr(cand, "content", None) or {}
            if hasattr(content, "parts"):
                for p in content.parts:
                    if getattr(p, "text", None):
                        raw_text += p.text

    parsed = safe_parse_json(raw_text)
    heuristics = detect_attributes_and_emotion(review_text)

    if not parsed:
        parsed = {
            "sentiment": sentiment,
            "emotion": heuristics["emotion"],
            "attributes": heuristics["attributes"],
            "star_rating": star_rating_int,
            "reply": build_reply_template(customer_name_norm, store_canonical, star_rating_int, sentiment),
        }

    parsed.setdefault("star_rating", star_rating_int)
    parsed.setdefault("sentiment", sentiment)
    parsed.setdefault("emotion", heuristics["emotion"])
    parsed.setdefault("attributes", heuristics["attributes"])

    if "reply" in parsed and parsed["reply"]:
        parsed["reply"] = enforce_customer_name_in_reply(parsed["reply"], customer_name_norm, store_canonical, star_rating_int)
    else:
        parsed["reply"] = enforce_customer_name_in_reply(
            build_reply_template(customer_name_norm, store_canonical, star_rating_int, sentiment),
            customer_name_norm, store_canonical, star_rating_int
        )

    return {"parsed": parsed, "quality_score": 75}