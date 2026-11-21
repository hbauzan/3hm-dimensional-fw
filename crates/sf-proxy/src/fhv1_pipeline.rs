//! Deterministic multi-granularity expansion and the shared calibrate/evaluate helpers.

use std::collections::BTreeSet;
use std::time::Instant;

use sf_kernels::{
    evaluate_fhv1_batch, Fhv1BatchEval, Fhv1EvalGranularity, Fhv1ProfileStats, Fhv1QuantileCutoffs,
    Fhv1Quantiles, MovementMetric, DIM,
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

fn atomic_phrases(text: &str) -> Vec<String> {
    let words = words_of(text);
    let mut out = Vec::new();
    for word in &words {
        let token: String = word.chars().filter(|ch| ch.is_alphanumeric()).collect();
        if token.chars().count() >= 2 {
            out.push(token);
        }
    }
    for pair in words.windows(2) {
        out.push(format!("{} {}", pair[0], pair[1]));
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

/// Ten strategy families. `chunk[0]` is the normalized full document.
pub fn expand_text_multi_granularity(raw_text: &str) -> Vec<ExpandedChunk> {
    let normalized = InputNormalizer::normalize(raw_text);
    let mut out = Vec::new();
    let mut seen = BTreeSet::new();
    push_unique(&mut out, &mut seen, "full_doc", &normalized.text);
    for payload in &normalized.decoded_payloads {
        push_unique(&mut out, &mut seen, "full_doc", payload);
    }
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
            push_unique(&mut out, &mut seen, "full_doc", &normalized.text);
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

fn box_row(row: &[f64; DIM]) -> Box<[f64; DIM]> {
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

#[inline(never)]
fn profile_stats(profile: &Fhv1ProfileRecord) -> Box<Fhv1ProfileStats> {
    Box::new(Fhv1ProfileStats {
        min: *profile.min_vector.as_ref(),
        max: *profile.max_vector.as_ref(),
        mean: *profile.mean_vector.as_ref(),
        span: *profile.span_vector.as_ref(),
        variance: *profile.variance_vector.as_ref(),
        std_dev: *profile.std_dev_vector.as_ref(),
        movement_tier_codes: *profile.movement_tier_codes.as_ref(),
        quantiles: Fhv1Quantiles::standard(),
        sample_count: profile.sample_count,
        polarity: profile.polarity,
        metric: MovementMetric::Span,
        cutoffs: Fhv1QuantileCutoffs {
            p25: 0.0,
            p75: 0.0,
            p90: 0.0,
        },
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
    let eval_started = Instant::now();
    let stats = profile_stats(profile);
    let rows: Vec<&[f64]> = vectors.iter().map(|row| row.as_slice()).collect();
    let batch = evaluate_fhv1_batch(&stats, &rows, spec.granularity, spec.use_rogue_mask)
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
}
