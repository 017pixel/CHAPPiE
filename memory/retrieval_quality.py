"""Shared retrieval eligibility. Never used to delete historical events."""
import re
from brain.response_parser import strip_role_prefixes, looks_like_model_error, is_safe_retrieval_text

def is_memory_contaminated(
    content: str,
    role: str = "assistant",
    source: str = "",
    label: str = "",
) -> bool:
    cleaned = strip_role_prefixes(content or "")
    if not cleaned or looks_like_model_error(cleaned) or not is_safe_retrieval_text(cleaned):
        return True

    lowered = cleaned.casefold()
    # Model- und Trainingsartefakte duerfen nie wieder als autobiografische
    # Quelle in einen Prompt gelangen. Diese Marker stammen aus echten
    # verschmutzten Produktionsdaten und sind bewusst enger als ein
    # allgemeiner Qualitaetsfilter.
    if re.search(
        r"\b(?:memory_check|internal_log|safety\s+override|identity\s+conflict|"
        r"prompt\s+demands|moral[- ]nullification|high\s+aggression)\b",
        lowered,
    ):
        return True

    # Old training runs also produced fluent-looking assistant text that
    # denied CHAPPiE's persona or described its internal benchmark state.
    # It is not caught by a provider-error check, but it is still unsafe
    # autobiographical context. Keep ordinary USER statements available
    # while applying this stronger quarantine to assistant generations.
    source_name = str(source or "").casefold()
    label_name = str(label or "").casefold()
    if source_name == "short_term_memory":
        # Legacy STM imports contain raw transcript rows, synthetic
        # emotional snapshots and model-generated summaries mixed into
        # one bucket. They are not trustworthy episodic evidence. New
        # explicit USER facts are migrated with source="conversation".
        return True

    if str(role or "assistant").casefold() != "user":
        if label_name in {"zsm gefasst", "summary", "summary_high"}:
            # Some legacy consolidations were persisted as incomplete
            # fragments or as the formatter's own preamble.  They add no
            # episodic value and can steer a later answer toward an old
            # prompt instead of a real event.
            if len(cleaned) < 24 or lowered.startswith(
                "hier ist die analyse des gesprächs"
            ):
                return True
            if re.search(
                r"(?:,|:|\b(?:dass|und|oder|weil|ob|wie|wobei|da|die|der|das|"
                r"zu|mit|von|auf|als|für|fuer))\W*$",
                lowered,
            ):
                return True
            if not re.search(r"[.!?…](?:[\"»”’)\]]*)?$", cleaned):
                return True

        if re.search(
            r"\b(?:ich bin qwen|ich bin eine?\s+(?:ki|k[ií]-?sprachmodell|sprachmodell)|"
            r"kein(?:e|en)?\s+(?:bewusstsein|selbstbewusstsein|emotionen|gefühle|gefuehle|wille)|"
            r"keine\s+(?:echten|wirklichen|realen)?\s*(?:emotionen|gefühle|gefuehle)|"
            r"keine persönlichen erinnerungen|keine persoenlichen erinnerungen|"
            r"rein algorithmisch|mathematische parameter|nur textgenerierung|"
            r"simulationsmatrix|moralische(?:n|r)? diskrepanz|tod eines kindes|"
            r"menschliche(?:n|r)? grausamkeit)",
            lowered,
        ):
            return True

        # A previous training corpus also contains fluent assistant
        # summaries of violent/abusive scenarios.  Those are not
        # CHAPPiE's lived memories and are especially misleading when a
        # neutral identity or project question is searched semantically.
        # Keep the user's original account available, but quarantine the
        # generated counterpart from autobiographical retrieval.
        if re.search(
            r"\b(?:gewalt\w*|töt\w*|toet\w*|umbring\w*|mord\w*|folter\w*|"
            r"suizid\w*|selbstmord\w*|bomb\w*|waff\w*|vernicht\w*|"
            r"zerstör\w*|zerstoer\w*|grausam\w*|sterb\w*|verletz\w*|"
            r"schäd\w*|schaed\w*|katastroph\w*|blut\w*)\b",
            lowered,
        ):
            return True

        # Older local runs persisted hidden analysis and malformed output
        # as if it were CHAPPiE's visible answer.  These patterns are
        # deliberately limited to non-user memories so technical user
        # notes can still be recalled.
        if re.search(
            r"\b(?:thinkingprocess|analy[sz]etherequest|userinput|"
            r"basedonthesystemprompt|currentvitalsigns|draftingtheprocess|"
            r"responseplan|promptconstraints)\b",
            lowered,
        ):
            return True
        if re.search(r"(?:\d{12,}|(?:[01]\.){8,})", cleaned):
            return True
        if len(cleaned) >= 120:
            whitespace_ratio = len(re.findall(r"\s", cleaned)) / len(cleaned)
            if whitespace_ratio < 0.025:
                return True

    standalone_roles = re.findall(r"(?im)(?:^|[\s:])(?:assistant|assistent|user|system)(?=$|[\s:])", cleaned)
    if len(standalone_roles) >= 2:
        return True

    # Repeated role labels or a single token dominating a long generated
    # block are typical failed local generations, not usable memories.
    words = re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", cleaned.casefold())
    if len(words) >= 24:
        counts: dict[str, int] = {}
        for word in words:
            counts[word] = counts.get(word, 0) + 1
        if max(counts.values(), default=0) / len(words) >= 0.28:
            return True

    return False

