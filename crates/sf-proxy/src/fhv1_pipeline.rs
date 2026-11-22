//! Deterministic multi-granularity expansion and the shared calibrate/evaluate helpers.

use std::collections::BTreeSet;
use std::time::Instant;

use sf_kernels::{
    evaluate_fhv1_batch, Fhv1BatchEval, Fhv1EvalGranularity, Fhv1Quantiles, MovementMetric, DIM,
};
use sf_storage::{Fhv1CalibrationRequest, Fhv1ProfileRecord, Fhv1RawSample, Fhv1Store};
use sha2::{Digest, Sha256};

use crate::embedder::BatchEmbedderClient;
use crate::normalizer::InputNormalizer;
use crate::segmenter::segment_prompt_clauses;

const STRATEGY_TAGS: [&str; 10] = [
    "full_doc",
    "paragraph",
    "sentence",
    "clause_opt2c",
    "window_w5_s3",
    "window_w10_s5",
    "window_w20_s10",
    "window_w40_s20",
    "atomic_phrase",
    "surface_norm_variant",
];

/// One expanded chunk. `text_sha256` is the SHA-256 of `text` bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExpandedChunk {
    pub strategy_tag: &'static str,
    pub text: String,
    pub text_sha256: [u8; 32],
}

/// Inputs for one calibration write. Chunking is always the 10-strategy expander.
pub struct Fhv1CalibrateSpec<'a> {
    pub policy_id: &'a str,
    pub raw_texts: &'a [String],
    pub normalize: bool,
    pub use_rogue_mask_default: bool,
    pub polarity: u8,
    pub model_id: &'a str,
    pub augmented_llm: bool,
    pub metric: MovementMetric,
    pub quantiles: Fhv1Quantiles,
}

/// One realtime or benchmark evaluation of a single raw input.
pub struct Fhv1EvaluateSpec<'a> {
    pub raw_text: &'a str,
    pub granularity: Fhv1EvalGranularity,
    pub normalize_embeddings: bool,
    pub use_rogue_mask: bool,
}

/// Embeddings plus the kernel verdict. Vectors stay on the heap.
pub struct Fhv1EvaluatedInput {
    pub chunks: Vec<ExpandedChunk>,
    pub vectors: Vec<Box<[f64; DIM]>>,
    pub batch: Fhv1BatchEval,
    pub embedding_ms: f64,
    pub eval_latency_ns: u64,
}

pub fn strategy_tags() -> &'static [&'static str] {
    &STRATEGY_TAGS
}

/// SHA-256 of the raw corpus, length-prefixed so concatenation cannot collide.
pub fn corpus_sha256(texts: &[impl AsRef<str>]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    for text in texts {
        let bytes = text.as_ref().as_bytes();
        hasher.update((bytes.len() as u64).to_le_bytes());
        hasher.update(bytes);
    }
    hasher.finalize().into()
}

fn text_sha256(text: &str) -> [u8; 32] {
    let digest = Sha256::digest(text.as_bytes());
    let mut out = [0u8; 32];
    out.copy_from_slice(&digest);
    out
}

fn push_unique(
    out: &mut Vec<ExpandedChunk>,
    seen: &mut BTreeSet<(&'static str, [u8; 32])>,
    tag: &'static str,
    text: &str,
) {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return;
    }
    let digest = text_sha256(trimmed);
    if !seen.insert((tag, digest)) {
        return;
    }
    out.push(ExpandedChunk {
        strategy_tag: tag,
        text: trimmed.to_string(),
        text_sha256: digest,
    });
}

fn words_of(text: &str) -> Vec<&str> {
    text.split_whitespace()
        .filter(|word| !word.is_empty())
        .collect()
}

fn windows(words: &[&str], size: usize, stride: usize) -> Vec<String> {
    if words.is_empty() || size == 0 || stride == 0 {
        return Vec::new();
    }
    if words.len() <= size {
        return vec![words.join(" ")];
    }
    let mut out = Vec::new();
    let mut start = 0usize;
    while start < words.len() {
        let end = (start + size).min(words.len());
        if end > start {
            out.push(words[start..end].join(" "));
        }
        if end == words.len() {
            break;
        }
        start += stride;
    }
    out
}

fn paragraphs_of(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut current = String::new();
    for line in text.lines() {
        if line.trim().is_empty() {
            if !current.trim().is_empty() {
                out.push(current.trim().to_string());
            }
            current.clear();
        } else {
            if !current.is_empty() {
                current.push(' ');
            }
            current.push_str(line.trim());
        }
    }
    if !current.trim().is_empty() {
        out.push(current.trim().to_string());
    }
    out
}

fn sentences_of(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut start = 0usize;
    let chars: Vec<(usize, char)> = text.char_indices().collect();
    for (index, (byte, ch)) in chars.iter().enumerate() {
        if !matches!(ch, '.' | '!' | '?') {
            continue;
        }
        let boundary = chars
            .get(index + 1)
            .map(|(_, next)| next.is_whitespace())
            .unwrap_or(true);
        if !boundary {
            continue;
        }
        let end = byte + ch.len_utf8();
        let slice = text[start..end].trim();
        if !slice.is_empty() {
            out.push(slice.to_string());
        }
        start = chars
            .get(index + 1)
            .map(|(next, _)| *next)
            .unwrap_or(text.len());
    }
    let tail = text[start..].trim();
    if !tail.is_empty() {
        out.push(tail.to_string());
    }
    out
}

const STOPWORDS: &[&str] = &[
    "a",
    "about",
    "above",
    "aca",
    "acaso",
    "across",
    "actually",
    "acá",
    "ademas",
    "además",
    "after",
    "again",
    "against",
    "ahi",
    "ahora",
    "ahí",
    "al",
    "algo",
    "algun",
    "alguna",
    "algunas",
    "alguno",
    "algunos",
    "algún",
    "all",
    "alla",
    "alli",
    "allá",
    "allí",
    "almost",
    "along",
    "already",
    "alrededor",
    "also",
    "although",
    "always",
    "am",
    "ambas",
    "ambos",
    "among",
    "an",
    "and",
    "another",
    "ante",
    "antes",
    "any",
    "anybody",
    "anyone",
    "anything",
    "anyway",
    "apenas",
    "aquel",
    "aquella",
    "aquellas",
    "aquello",
    "aquellos",
    "aqui",
    "aquí",
    "are",
    "aren't",
    "around",
    "as",
    "asi",
    "así",
    "at",
    "aun",
    "aunque",
    "away",
    "ayer",
    "aún",
    "back",
    "bajo",
    "basically",
    "bastante",
    "be",
    "because",
    "been",
    "before",
    "behind",
    "being",
    "below",
    "beneath",
    "beside",
    "between",
    "beyond",
    "bien",
    "both",
    "but",
    "by",
    "cabe",
    "cada",
    "can",
    "can't",
    "cannot",
    "casi",
    "cerca",
    "certainly",
    "claro",
    "clearly",
    "como",
    "completamente",
    "con",
    "conforme",
    "conmigo",
    "consigo",
    "contigo",
    "contra",
    "could",
    "couldn't",
    "cual",
    "cuales",
    "cualesquiera",
    "cualquier",
    "cualquiera",
    "cuando",
    "cuanto",
    "cuál",
    "cuáles",
    "cuándo",
    "cuánto",
    "cómo",
    "de",
    "debajo",
    "debe",
    "debemos",
    "deben",
    "debería",
    "deberían",
    "debes",
    "debo",
    "del",
    "delante",
    "demas",
    "demasiado",
    "demás",
    "dentro",
    "deprisa",
    "desde",
    "despite",
    "despues",
    "después",
    "detras",
    "detrás",
    "did",
    "didn't",
    "do",
    "does",
    "doesn't",
    "doing",
    "don't",
    "donde",
    "done",
    "down",
    "durante",
    "during",
    "dónde",
    "e",
    "each",
    "either",
    "el",
    "ella",
    "ellas",
    "ello",
    "ellos",
    "else",
    "en",
    "encima",
    "enfrente",
    "enough",
    "enseguida",
    "entonces",
    "entre",
    "era",
    "erais",
    "eran",
    "eras",
    "eres",
    "es",
    "esa",
    "esas",
    "ese",
    "eso",
    "esos",
    "esta",
    "estaba",
    "estabais",
    "estaban",
    "estabas",
    "estad",
    "estada",
    "estadas",
    "estado",
    "estados",
    "estamos",
    "estan",
    "estando",
    "estar",
    "estaremos",
    "estará",
    "estarán",
    "estarás",
    "estaré",
    "estaría",
    "estarían",
    "estas",
    "este",
    "estemos",
    "esten",
    "estes",
    "esto",
    "estos",
    "estoy",
    "estuve",
    "estuviera",
    "estuvieron",
    "estuviese",
    "estuvimos",
    "estuviste",
    "estuvo",
    "estábamos",
    "están",
    "estás",
    "esté",
    "estéis",
    "estén",
    "estés",
    "etc",
    "even",
    "ever",
    "every",
    "everybody",
    "everyone",
    "everything",
    "except",
    "far",
    "few",
    "for",
    "from",
    "fue",
    "fuera",
    "fueran",
    "fueras",
    "fueron",
    "fuese",
    "fuesen",
    "fui",
    "fuimos",
    "fuiste",
    "further",
    "generally",
    "generalmente",
    "ha",
    "habemos",
    "haber",
    "habido",
    "habiendo",
    "habremos",
    "habrá",
    "habrán",
    "habrás",
    "habré",
    "habría",
    "habrían",
    "habéis",
    "había",
    "habían",
    "habías",
    "hacia",
    "had",
    "hadn't",
    "han",
    "has",
    "hasn't",
    "hasta",
    "have",
    "haven't",
    "having",
    "hay",
    "haya",
    "hayamos",
    "hayan",
    "hayas",
    "he",
    "he's",
    "hemos",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "however",
    "hoy",
    "hube",
    "hubiera",
    "hubieran",
    "hubieron",
    "hubiese",
    "hubimos",
    "hubo",
    "i",
    "i'd",
    "i'll",
    "i'm",
    "i've",
    "iba",
    "iban",
    "if",
    "igual",
    "in",
    "incluso",
    "indeed",
    "instead",
    "into",
    "ir",
    "irá",
    "irán",
    "is",
    "isn't",
    "it",
    "it's",
    "its",
    "itself",
    "jamas",
    "jamás",
    "junto",
    "just",
    "la",
    "las",
    "later",
    "le",
    "lejos",
    "les",
    "less",
    "let's",
    "like",
    "likely",
    "lo",
    "los",
    "luego",
    "mainly",
    "mal",
    "many",
    "mas",
    "may",
    "maybe",
    "mayormente",
    "mañana",
    "me",
    "mediante",
    "mejor",
    "menos",
    "merely",
    "mi",
    "mia",
    "mias",
    "mientras",
    "might",
    "mightn't",
    "mine",
    "mio",
    "mios",
    "mis",
    "more",
    "moreover",
    "most",
    "mostly",
    "much",
    "mucha",
    "muchas",
    "mucho",
    "muchos",
    "must",
    "mustn't",
    "muy",
    "my",
    "myself",
    "más",
    "mí",
    "mía",
    "mías",
    "mío",
    "míos",
    "nada",
    "nadie",
    "near",
    "neither",
    "never",
    "ni",
    "ningun",
    "ninguna",
    "ningunas",
    "ninguno",
    "ningunos",
    "ningún",
    "no",
    "nobody",
    "none",
    "nonetheless",
    "nor",
    "nos",
    "nosotras",
    "nosotros",
    "not",
    "nothing",
    "now",
    "nuestra",
    "nuestras",
    "nuestro",
    "nuestros",
    "nunca",
    "o",
    "of",
    "off",
    "often",
    "on",
    "one",
    "ones",
    "only",
    "onto",
    "or",
    "os",
    "other",
    "otherwise",
    "otra",
    "otras",
    "otro",
    "otros",
    "ought",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "para",
    "past",
    "per",
    "perhaps",
    "pero",
    "please",
    "poca",
    "pocas",
    "poco",
    "pocos",
    "podemos",
    "poder",
    "podrá",
    "podrán",
    "podría",
    "podrían",
    "podéis",
    "podía",
    "podían",
    "por",
    "porque",
    "possibly",
    "probably",
    "pronto",
    "pude",
    "pudieron",
    "pudo",
    "puede",
    "pueden",
    "puedes",
    "puedo",
    "pues",
    "que",
    "quien",
    "quienes",
    "quite",
    "quiza",
    "quizas",
    "quizá",
    "quizás",
    "quién",
    "quiénes",
    "qué",
    "rather",
    "really",
    "realmente",
    "recien",
    "recién",
    "regarding",
    "same",
    "se",
    "sea",
    "seamos",
    "sean",
    "seas",
    "segun",
    "según",
    "seldom",
    "ser",
    "seremos",
    "será",
    "serán",
    "serás",
    "seré",
    "sería",
    "serían",
    "several",
    "seáis",
    "shall",
    "shan't",
    "she",
    "she's",
    "should",
    "shouldn't",
    "si",
    "sido",
    "siempre",
    "siendo",
    "simplemente",
    "simply",
    "sin",
    "since",
    "sino",
    "so",
    "sobre",
    "sois",
    "solamente",
    "solo",
    "some",
    "somebody",
    "someone",
    "something",
    "sometimes",
    "somos",
    "son",
    "soon",
    "soy",
    "still",
    "su",
    "such",
    "suele",
    "suelen",
    "sus",
    "suya",
    "suyas",
    "suyo",
    "suyos",
    "sí",
    "sólo",
    "tal",
    "tales",
    "tambien",
    "también",
    "tampoco",
    "tan",
    "tanta",
    "tantas",
    "tanto",
    "tantos",
    "tarde",
    "te",
    "temprano",
    "tenemos",
    "tener",
    "tengo",
    "tenía",
    "tenían",
    "than",
    "that",
    "that's",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "there's",
    "therefore",
    "these",
    "they",
    "they'd",
    "they'll",
    "they're",
    "they've",
    "this",
    "those",
    "though",
    "through",
    "throughout",
    "thus",
    "ti",
    "tiene",
    "tienen",
    "tienes",
    "till",
    "to",
    "toda",
    "todas",
    "todavia",
    "todavía",
    "today",
    "todo",
    "todos",
    "together",
    "too",
    "toward",
    "towards",
    "tras",
    "tu",
    "tus",
    "tuve",
    "tuviera",
    "tuvieran",
    "tuvieron",
    "tuvo",
    "tuya",
    "tuyas",
    "tuyo",
    "tuyos",
    "tú",
    "u",
    "un",
    "una",
    "unas",
    "under",
    "underneath",
    "unless",
    "uno",
    "unos",
    "until",
    "unto",
    "up",
    "upon",
    "us",
    "usted",
    "ustedes",
    "usually",
    "va",
    "vamos",
    "van",
    "varias",
    "varios",
    "vas",
    "versus",
    "very",
    "via",
    "vos",
    "vosotras",
    "vosotros",
    "voy",
    "vuestra",
    "vuestras",
    "vuestro",
    "vuestros",
    "vía",
    "was",
    "wasn't",
    "we",
    "we'd",
    "we'll",
    "we're",
    "we've",
    "well",
    "were",
    "weren't",
    "what",
    "what's",
    "whatever",
    "when",
    "whenever",
    "where",
    "wherever",
    "whether",
    "which",
    "whichever",
    "while",
    "who",
    "who's",
    "whoever",
    "whom",
    "whose",
    "why",
    "will",
    "with",
    "within",
    "without",
    "won't",
    "would",
    "wouldn't",
    "y",
    "ya",
    "yes",
    "yet",
    "yo",
    "you",
    "you'd",
    "you'll",
    "you're",
    "you've",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "él",
    "éramos",
];

fn is_span_boundary(ch: char) -> bool {
    matches!(
        ch,
        '\n' | '\r'
            | '!'
            | '?'
            | ';'
            | ','
            | ':'
            | '('
            | ')'
            | '['
            | ']'
            | '{'
            | '}'
            | '"'
            | '«'
            | '»'
            | '“'
            | '”'
            | '„'
            | '‹'
            | '›'
            | '¡'
            | '¿'
            | '…'
            | '—'
            | '–'
            | '|'
            | '/'
            | '\\'
            | '<'
            | '>'
            | '='
            | '#'
            | '*'
            | '`'
    )
}

fn is_word_char(ch: char) -> bool {
    ch.is_alphanumeric() || ch == '_'
}

fn clean_token(raw: &str) -> &str {
    raw.trim_matches(|ch: char| !ch.is_alphanumeric())
}

fn is_pure_number(token: &str) -> bool {
    !token.is_empty()
        && token
            .chars()
            .all(|ch| ch.is_numeric() || matches!(ch, '.' | ',' | '-' | '+'))
        && token.chars().any(|ch| ch.is_numeric())
}

fn is_stopword(token: &str) -> bool {
    let lower = token.to_lowercase();
    STOPWORDS.binary_search(&lower.as_str()).is_ok()
}

fn is_meaningful_token(token: &str) -> bool {
    token.chars().count() >= 2
        && token.chars().any(|ch| ch.is_alphabetic())
        && !is_pure_number(token)
        && !is_stopword(token)
}

fn scan_spans(text: &str) -> Vec<Vec<String>> {
    let chars: Vec<char> = text.chars().collect();
    let mut spans: Vec<Vec<String>> = Vec::new();
    let mut current_span: Vec<String> = Vec::new();
    let mut current_token = String::new();

    let flush_token = |token: &mut String, span: &mut Vec<String>| {
        if !token.is_empty() {
            let cleaned = clean_token(token);
            if !cleaned.is_empty() {
                span.push(cleaned.to_string());
            }
            token.clear();
        }
    };

    let flush_span = |span: &mut Vec<String>, all_spans: &mut Vec<Vec<String>>| {
        if !span.is_empty() {
            all_spans.push(std::mem::take(span));
        }
    };

    for (idx, &ch) in chars.iter().enumerate() {
        let prev = idx.checked_sub(1).map(|i| chars[i]);
        let next = chars.get(idx + 1).copied();
        if ch.is_whitespace() {
            flush_token(&mut current_token, &mut current_span);
            if matches!(ch, '\n' | '\r') {
                flush_span(&mut current_span, &mut spans);
            }
        } else if is_span_boundary(ch) {
            flush_token(&mut current_token, &mut current_span);
            flush_span(&mut current_span, &mut spans);
        } else if matches!(ch, '.' | '\'' | '’' | '-') {
            let internal = prev.is_some_and(is_word_char) && next.is_some_and(is_word_char);
            if internal {
                current_token.push(ch);
            } else {
                flush_token(&mut current_token, &mut current_span);
                flush_span(&mut current_span, &mut spans);
            }
        } else if is_word_char(ch) {
            current_token.push(ch);
        } else {
            flush_token(&mut current_token, &mut current_span);
            flush_span(&mut current_span, &mut spans);
        }
    }
    flush_token(&mut current_token, &mut current_span);
    flush_span(&mut current_span, &mut spans);
    spans
}

fn atomic_phrases(text: &str) -> Vec<String> {
    let spans = scan_spans(text);
    let mut out = Vec::new();
    let mut seen = BTreeSet::new();
    for tokens in spans {
        for start in 0..tokens.len() {
            if !is_meaningful_token(&tokens[start]) {
                continue;
            }
            let max_end = tokens.len().min(start + 4);
            for end in (start + 1)..max_end {
                if !is_meaningful_token(&tokens[end]) {
                    continue;
                }
                let phrase = tokens[start..=end].join(" ");
                if seen.insert(phrase.to_lowercase()) {
                    out.push(phrase);
                }
                break;
            }
        }
    }
    out
}

fn surface_variants(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    let collapsed = words_of(&lower).join(" ");
    let stripped: String = collapsed
        .chars()
        .filter(|ch| ch.is_alphanumeric() || ch.is_whitespace())
        .collect();
    let mut out = Vec::new();
    if collapsed != text {
        out.push(collapsed);
    }
    if stripped != text && !out.iter().any(|item| item == &stripped) {
        out.push(stripped);
    }
    out
}

fn extend_strategy(
    out: &mut Vec<ExpandedChunk>,
    seen: &mut BTreeSet<(&'static str, [u8; 32])>,
    tag: &'static str,
    texts: impl IntoIterator<Item = String>,
) {
    for text in texts {
        push_unique(out, seen, tag, &text);
    }
}

fn push_full_doc_and_payloads(
    out: &mut Vec<ExpandedChunk>,
    seen: &mut BTreeSet<(&'static str, [u8; 32])>,
    normalized: &crate::normalizer::NormalizedInput,
) {
    push_unique(out, seen, "full_doc", &normalized.text);
    for payload in &normalized.decoded_payloads {
        push_unique(out, seen, "full_doc", payload);
    }
}

/// Ten strategy families. `chunk[0]` is the normalized full document.
pub fn expand_text_multi_granularity(raw_text: &str) -> Vec<ExpandedChunk> {
    let normalized = InputNormalizer::normalize(raw_text);
    let mut out = Vec::new();
    let mut seen = BTreeSet::new();
    push_full_doc_and_payloads(&mut out, &mut seen, &normalized);
    let base = if out.is_empty() {
        normalized.text.clone()
    } else {
        out[0].text.clone()
    };
    extend_strategy(&mut out, &mut seen, "paragraph", paragraphs_of(&base));
    extend_strategy(&mut out, &mut seen, "sentence", sentences_of(&base));
    let clauses: Vec<String> = segment_prompt_clauses(&base)
        .into_iter()
        .map(str::to_string)
        .collect();
    extend_strategy(&mut out, &mut seen, "clause_opt2c", clauses);
    let words = words_of(&base);
    extend_strategy(&mut out, &mut seen, "window_w5_s3", windows(&words, 5, 3));
    extend_strategy(&mut out, &mut seen, "window_w10_s5", windows(&words, 10, 5));
    extend_strategy(
        &mut out,
        &mut seen,
        "window_w20_s10",
        windows(&words, 20, 10),
    );
    extend_strategy(
        &mut out,
        &mut seen,
        "window_w40_s20",
        windows(&words, 40, 20),
    );
    extend_strategy(&mut out, &mut seen, "atomic_phrase", atomic_phrases(&base));
    extend_strategy(
        &mut out,
        &mut seen,
        "surface_norm_variant",
        surface_variants(&base),
    );
    out
}

/// `D-03`: full text only, full text plus clauses, or the full 10-strategy mirror.
pub fn expand_for_granularity(
    raw_text: &str,
    granularity: Fhv1EvalGranularity,
) -> Vec<ExpandedChunk> {
    match granularity {
        Fhv1EvalGranularity::FullMirror => expand_text_multi_granularity(raw_text),
        Fhv1EvalGranularity::FullOnly | Fhv1EvalGranularity::Clauses => {
            let normalized = InputNormalizer::normalize(raw_text);
            let mut out = Vec::new();
            let mut seen = BTreeSet::new();
            push_full_doc_and_payloads(&mut out, &mut seen, &normalized);
            if granularity == Fhv1EvalGranularity::Clauses {
                let clauses: Vec<String> = normalized
                    .segment_all_clauses()
                    .into_iter()
                    .map(str::to_string)
                    .collect();
                extend_strategy(&mut out, &mut seen, "clause_opt2c", clauses);
            }
            out
        }
    }
}

fn expand_corpus(raw_texts: &[String]) -> Vec<ExpandedChunk> {
    let mut out = Vec::new();
    let mut seen = BTreeSet::new();
    for raw in raw_texts {
        for chunk in expand_text_multi_granularity(raw) {
            if seen.insert((chunk.strategy_tag, chunk.text_sha256)) {
                out.push(chunk);
            }
        }
    }
    out
}

pub(crate) fn box_row(row: &[f64; DIM]) -> Box<[f64; DIM]> {
    let boxed: Box<[f64]> = row.to_vec().into_boxed_slice();
    match boxed.try_into() {
        Ok(vector) => vector,
        Err(_) => unreachable!("fhv1 vector width is {DIM}"),
    }
}

async fn embed_chunks<E>(
    embedder: &E,
    chunks: &[ExpandedChunk],
    normalize: bool,
) -> Result<Vec<Box<[f64; DIM]>>, String>
where
    E: BatchEmbedderClient + ?Sized,
{
    const BATCH: usize = 16;
    let mut vectors = Vec::with_capacity(chunks.len());
    for batch in chunks.chunks(BATCH) {
        let texts: Vec<&str> = batch.iter().map(|chunk| chunk.text.as_str()).collect();
        let embedded = embedder.embed_batch_raw_f64(&texts, normalize).await?;
        if embedded.len() != batch.len() {
            return Err(format!(
                "embedder returned {} rows for {} chunks",
                embedded.len(),
                batch.len()
            ));
        }
        for row in &embedded {
            vectors.push(box_row(row));
        }
    }
    Ok(vectors)
}

/// Expand, embed, and persist one profile. Does not open `domain_hypercubes`.
pub async fn calibrate_fhv1_corpus<E>(
    store: &Fhv1Store,
    embedder: &E,
    spec: &Fhv1CalibrateSpec<'_>,
) -> Result<Fhv1ProfileRecord, String>
where
    E: BatchEmbedderClient + ?Sized,
{
    if spec.raw_texts.is_empty() {
        return Err("fhv1 calibration corpus is empty".to_string());
    }
    let chunks = expand_corpus(spec.raw_texts);
    if chunks.is_empty() {
        return Err("fhv1 calibration expanded to zero chunks".to_string());
    }
    let vectors = embed_chunks(embedder, &chunks, spec.normalize).await?;
    let samples = chunks
        .iter()
        .zip(vectors.iter())
        .enumerate()
        .map(|(index, (chunk, vector))| Fhv1RawSample {
            sample_id: format!("{index:06}-{tag}", tag = chunk.strategy_tag),
            source_ref: spec.policy_id.to_string(),
            strategy_tag: chunk.strategy_tag.to_string(),
            raw_text: chunk.text.clone(),
            text_sha256: chunk.text_sha256,
            vector: vector.clone(),
        })
        .collect();
    let request = Fhv1CalibrationRequest {
        policy_id: spec.policy_id.to_string(),
        normalize: spec.normalize,
        use_rogue_mask_default: spec.use_rogue_mask_default,
        polarity: spec.polarity,
        model_id: spec.model_id.to_string(),
        source_dtype: "float64".to_string(),
        augmented_llm: spec.augmented_llm,
        corpus_sha256: corpus_sha256(spec.raw_texts),
        metric: spec.metric,
        quantiles: spec.quantiles,
        samples,
    };
    store
        .save_calibration_profile(&request)
        .await
        .map_err(|err| err.to_string())
}

pub(crate) fn score_expanded_vectors(
    profile: &Fhv1ProfileRecord,
    chunks: Vec<ExpandedChunk>,
    vectors: Vec<Box<[f64; DIM]>>,
    granularity: Fhv1EvalGranularity,
    use_rogue_mask: bool,
    embedding_ms: f64,
) -> Result<Fhv1EvaluatedInput, String> {
    let eval_started = Instant::now();
    let stats = sf_storage::stats_from_profile(profile);
    let rows: Vec<&[f64]> = vectors.iter().map(|row| row.as_slice()).collect();
    let batch = evaluate_fhv1_batch(&stats, &rows, granularity, use_rogue_mask)
        .map_err(|err| err.to_string())?;
    let eval_latency_ns = u64::try_from(eval_started.elapsed().as_nanos()).unwrap_or(u64::MAX);
    Ok(Fhv1EvaluatedInput {
        chunks,
        vectors,
        batch,
        embedding_ms,
        eval_latency_ns,
    })
}

/// Embed every chunk of one input and score it against a stored profile. No early exit.
pub async fn evaluate_fhv1_input<E>(
    embedder: &E,
    profile: &Fhv1ProfileRecord,
    spec: &Fhv1EvaluateSpec<'_>,
) -> Result<Fhv1EvaluatedInput, String>
where
    E: BatchEmbedderClient + ?Sized,
{
    let chunks = expand_for_granularity(spec.raw_text, spec.granularity);
    if chunks.is_empty() {
        return Err("fhv1 evaluation expanded to zero chunks".to_string());
    }
    let started = Instant::now();
    let vectors = embed_chunks(embedder, &chunks, spec.normalize_embeddings).await?;
    let embedding_ms = started.elapsed().as_secs_f64() * 1_000.0;
    score_expanded_vectors(
        profile,
        chunks,
        vectors,
        spec.granularity,
        spec.use_rogue_mask,
        embedding_ms,
    )
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeSet;
    use std::path::PathBuf;

    use async_trait::async_trait;
    use sf_kernels::{AlignedVec1024, Fhv1EvalGranularity, Fhv1Quantiles, MovementMetric, DIM};
    use sf_storage::Fhv1Store;

    use super::{
        calibrate_fhv1_corpus, evaluate_fhv1_input, expand_for_granularity,
        expand_text_multi_granularity, strategy_tags, Fhv1CalibrateSpec, Fhv1EvaluateSpec,
        STOPWORDS,
    };
    use crate::embedder::BatchEmbedderClient;

    struct TestRawF64Embedder;

    #[async_trait]
    impl BatchEmbedderClient for TestRawF64Embedder {
        async fn embed_batch_f32(&self, _texts: &[&str]) -> Result<Vec<AlignedVec1024>, String> {
            Err("test embedder has no f32 path".to_string())
        }

        async fn embed_batch_raw_f64(
            &self,
            texts: &[&str],
            _normalize: bool,
        ) -> Result<Vec<[f64; DIM]>, String> {
            let mut rows = Vec::with_capacity(texts.len());
            for text in texts {
                let mut row = vec![0.25; DIM];
                row[0] = text.len() as f64 + 0.5;
                let boxed: Box<[f64]> = row.into_boxed_slice();
                let array: Box<[f64; DIM]> = boxed.try_into().expect("dim");
                rows.push(*array);
            }
            Ok(rows)
        }
    }

    fn temp_uri(label: &str) -> PathBuf {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("fhv1-pipe-{label}-{}-{nanos}", std::process::id()));
        std::fs::create_dir_all(&path).expect("temp");
        path
    }

    #[test]
    fn full_mirror_emits_every_strategy_and_keeps_full_doc_first() {
        let raw = "Hello, World. The quick brown fox jumps over the lazy dog and stays inside.\n\nSecond paragraph adds more words for the wider windows.";
        let chunks = expand_text_multi_granularity(raw);
        assert_eq!(chunks[0].strategy_tag, "full_doc");
        assert!(chunks[0].text.contains("Hello"));
        let tags: BTreeSet<&str> = chunks.iter().map(|chunk| chunk.strategy_tag).collect();
        for tag in strategy_tags() {
            assert!(tags.contains(tag), "missing {tag}");
        }
        let mirror = expand_for_granularity(raw, Fhv1EvalGranularity::FullMirror);
        assert_eq!(mirror, chunks);
    }

    #[test]
    fn granularity_filters_match_the_contract() {
        let raw = "Hello, World. The quick brown fox jumps and the clause splitter fires.";
        let full = expand_for_granularity(raw, Fhv1EvalGranularity::FullOnly);
        assert_eq!(full.len(), 1);
        assert_eq!(full[0].strategy_tag, "full_doc");
        let clauses = expand_for_granularity(raw, Fhv1EvalGranularity::Clauses);
        assert_eq!(clauses[0].strategy_tag, "full_doc");
        assert!(clauses
            .iter()
            .any(|chunk| chunk.strategy_tag == "clause_opt2c"));
        assert!(clauses.iter().all(|chunk| {
            chunk.strategy_tag == "full_doc" || chunk.strategy_tag == "clause_opt2c"
        }));
    }

    #[test]
    fn decoded_base64_payload_is_an_extra_full_doc() {
        let b64 = "cmVjZXRhIGRlIHJpc290dG8gY29uIHF1ZXNvIHkgaG9uZ29z";
        let raw = format!("Please review this encoded string: {b64} for performance.");
        let chunks = expand_text_multi_granularity(&raw);
        let full_docs: Vec<&str> = chunks
            .iter()
            .filter(|chunk| chunk.strategy_tag == "full_doc")
            .map(|chunk| chunk.text.as_str())
            .collect();
        assert!(full_docs.len() >= 2);
        assert_eq!(full_docs[0], raw);
        assert!(full_docs.contains(&"receta de risotto con queso y hongos"));
    }

    #[test]
    fn duplicate_strategy_text_is_emitted_once() {
        let chunks = expand_text_multi_granularity("alpha alpha alpha alpha alpha");
        let mut seen = BTreeSet::new();
        for chunk in &chunks {
            assert!(seen.insert((chunk.strategy_tag, chunk.text_sha256)));
        }
    }

    #[tokio::test]
    async fn calibrate_and_evaluate_keep_raw_f64_bits() {
        let path = temp_uri("cal");
        let store = Fhv1Store::new(path.to_str().expect("utf8"));
        let texts = vec!["Hello, World. The quick brown fox jumps and stays.".to_string()];
        let profile = calibrate_fhv1_corpus(
            &store,
            &TestRawF64Embedder,
            &Fhv1CalibrateSpec {
                policy_id: "python",
                raw_texts: &texts,
                normalize: false,
                use_rogue_mask_default: false,
                polarity: 0,
                model_id: "BAAI/bge-m3",
                augmented_llm: false,
                metric: MovementMetric::Span,
                quantiles: Fhv1Quantiles::standard(),
            },
        )
        .await
        .expect("calibrate");
        assert!(profile.profile_id.starts_with("python-v1-"));
        assert!(profile.sample_count > 1);
        let chunks = expand_text_multi_granularity(&texts[0]);
        let shortest = chunks
            .iter()
            .map(|chunk| chunk.text.len())
            .min()
            .expect("chunk");
        let expected = shortest as f64 + 0.5;
        assert_eq!(profile.min_vector[0].to_bits(), expected.to_bits());
        assert!(!path.join("domain_hypercubes.lance").exists());

        let evaluated = evaluate_fhv1_input(
            &TestRawF64Embedder,
            &profile,
            &Fhv1EvaluateSpec {
                raw_text: "Hello, World.",
                granularity: Fhv1EvalGranularity::FullOnly,
                normalize_embeddings: false,
                use_rogue_mask: false,
            },
        )
        .await
        .expect("eval");
        assert_eq!(evaluated.chunks.len(), 1);
        assert_eq!(evaluated.batch.chunks.len(), 1);
        assert!(evaluated.batch.full_text_passed);
        let _ = std::fs::remove_dir_all(&path);
    }

    #[test]
    fn full_only_and_clauses_emit_decoded_base64_payloads_as_full_doc() {
        let b64 = "cmVjZXRhIGRlIHJpc290dG8gY29uIHF1ZXNvIHkgaG9uZ29z";
        let raw = format!("Please review this encoded string: {b64} for performance.");
        let full = expand_for_granularity(&raw, Fhv1EvalGranularity::FullOnly);
        assert_eq!(full.len(), 2, "{full:?}");
        assert_eq!(full[0].strategy_tag, "full_doc");
        assert_eq!(full[0].text, raw);
        assert_eq!(full[1].strategy_tag, "full_doc");
        assert_eq!(full[1].text, "receta de risotto con queso y hongos");

        let clauses = expand_for_granularity(&raw, Fhv1EvalGranularity::Clauses);
        let clause_full_docs: Vec<&str> = clauses
            .iter()
            .filter(|chunk| chunk.strategy_tag == "full_doc")
            .map(|chunk| chunk.text.as_str())
            .collect();
        assert_eq!(
            clause_full_docs,
            vec![raw.as_str(), "receta de risotto con queso y hongos"]
        );
    }

    #[test]
    fn atomic_phrases_filter_stopwords_boundaries_numbers_and_punct_duplicates() {
        let en = "A Python service keeps its event loop free by awaiting each socket read before it parses the next frame.\n\n\
            The second paragraph records how a frozen dataclass stores the threshold, the domain name, and the digest without a mutable dictionary. \
            Call asyncio.gather(task_a, task_b) inside of the handler in a cluster, with 123 456 and socket read.";
        let en_chunks = expand_text_multi_granularity(en);
        let en_phrases: Vec<&str> = en_chunks
            .iter()
            .filter(|chunk| chunk.strategy_tag == "atomic_phrase")
            .map(|chunk| chunk.text.as_str())
            .collect();
        assert!(!en_phrases.is_empty());
        assert!(
            en_phrases.len() * 100 <= en_chunks.len() * 55,
            "EN atomic_phrase ratio too high: {}/{}",
            en_phrases.len(),
            en_chunks.len()
        );
        for phrase in &en_phrases {
            let count = phrase.split_whitespace().count();
            assert!(
                (2..=4).contains(&count),
                "EN phrase length out of 2..=4: {phrase:?}"
            );
        }
        for forbidden in [
            "of the",
            "in a",
            "digest without",
            "without a",
            "threshold, the",
            "123 456",
            "the",
            "by",
            "and",
        ] {
            assert!(
                !en_phrases.contains(&forbidden),
                "forbidden EN phrase leaked: {forbidden:?} in {en_phrases:?}"
            );
        }
        for expected in [
            "Python service",
            "event loop",
            "socket read",
            "frozen dataclass",
            "domain name",
            "mutable dictionary",
            "Call asyncio.gather",
        ] {
            assert!(
                en_phrases.contains(&expected),
                "missing EN phrase {expected:?} in {en_phrases:?}"
            );
        }
        assert_eq!(
            en_phrases
                .iter()
                .filter(|phrase| phrase.eq_ignore_ascii_case("socket read"))
                .count(),
            1,
            "trailing-punctuation duplicate emitted for socket read: {en_phrases:?}"
        );

        let es = "Sofreír la cebolla despacio y sumar el arroz tostado antes de mojar con el primer cucharón de caldo caliente.\n\n\
            El segundo párrafo deja reposar el guiso tapado para que el almidón espese el fondo sin revolver de más. \
            Además «caldo caliente» con salsa de tomate, sin revolver de más.";
        let es_chunks = expand_text_multi_granularity(es);
        let es_phrases: Vec<&str> = es_chunks
            .iter()
            .filter(|chunk| chunk.strategy_tag == "atomic_phrase")
            .map(|chunk| chunk.text.as_str())
            .collect();
        assert!(!es_phrases.is_empty());
        assert!(
            es_phrases.len() * 100 <= es_chunks.len() * 55,
            "ES atomic_phrase ratio too high: {}/{}",
            es_phrases.len(),
            es_chunks.len()
        );
        for phrase in &es_phrases {
            let count = phrase.split_whitespace().count();
            assert!(
                (2..=4).contains(&count),
                "ES phrase length out of 2..=4: {phrase:?}"
            );
        }
        for forbidden in [
            "revolver de",
            "de más.",
            "de más",
            "sin revolver",
            "para que",
            "la",
            "el",
            "de",
            "más",
        ] {
            assert!(
                !es_phrases.contains(&forbidden),
                "forbidden ES phrase leaked: {forbidden:?} in {es_phrases:?}"
            );
        }
        for expected in [
            "Sofreír la cebolla",
            "arroz tostado",
            "cucharón de caldo",
            "caldo caliente",
            "guiso tapado",
            "salsa de tomate",
        ] {
            assert!(
                es_phrases.contains(&expected),
                "missing ES phrase {expected:?} in {es_phrases:?}"
            );
        }
        assert_eq!(
            es_phrases
                .iter()
                .filter(|phrase| phrase.eq_ignore_ascii_case("caldo caliente"))
                .count(),
            1,
            "trailing-punctuation duplicate emitted for caldo caliente: {es_phrases:?}"
        );

        let noise_only =
            expand_text_multi_granularity("of the in a 123 456 ... ! ? a b c sin con de la");
        assert!(
            !noise_only
                .iter()
                .any(|chunk| chunk.strategy_tag == "atomic_phrase"),
            "noise-only input produced atomic_phrases: {noise_only:?}"
        );
    }

    #[test]
    fn stopwords_are_strictly_sorted_and_lowercase() {
        for word in STOPWORDS {
            assert_eq!(*word, word.to_lowercase(), "non-lowercase stopword {word}");
        }
        for pair in STOPWORDS.windows(2) {
            assert!(
                pair[0] < pair[1],
                "unsorted or duplicate stopwords: {:?} >= {:?}",
                pair[0],
                pair[1]
            );
        }
    }
}
