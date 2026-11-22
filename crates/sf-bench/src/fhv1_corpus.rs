//! Canonical `fhv1` seed documents and file ingestion.

use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use crate::canonical_corpus::canonical_seed_corpus;

const PYTHON_CORPUS_JSONL: &str = include_str!("../fixtures/fhv1_corpus_python.jsonl");
const RECETA_CORPUS_JSONL: &str = include_str!("../fixtures/fhv1_corpus_receta.jsonl");

/// SHA-256 of one document. Used to drop duplicate ingested texts.
pub fn text_sha256(text: &str) -> [u8; 32] {
    let digest = Sha256::digest(text.as_bytes());
    let mut out = [0u8; 32];
    out.copy_from_slice(digest.as_slice());
    out
}

/// Curated offline base documents (`150–300` docs for `python` and `receta`; 16 seeds for other domains).
pub fn canonical_fhv1_documents(policy_id: &str) -> Result<Vec<String>, String> {
    match policy_id {
        "python" => parse_jsonl(PYTHON_CORPUS_JSONL).map(dedupe_documents),
        "receta" => parse_jsonl(RECETA_CORPUS_JSONL).map(dedupe_documents),
        _ => {
            let domain = canonical_seed_corpus()
                .iter()
                .find(|item| item.domain_id == policy_id)
                .ok_or_else(|| format!("unknown fhv1 policy '{policy_id}'"))?;
            Ok(domain
                .sentences
                .iter()
                .map(|line| (*line).to_string())
                .collect())
        }
    }
}

/// Read `.txt`, `.md`, and `.jsonl` documents. A directory is walked in sorted order.
pub fn read_corpus_path(path: &Path) -> Result<Vec<String>, String> {
    if path.is_dir() {
        let mut files = Vec::new();
        collect_files(path, &mut files)?;
        files.sort();
        let mut documents = Vec::new();
        for file in files {
            documents.extend(read_one_file(&file)?);
        }
        return Ok(dedupe_documents(documents));
    }
    read_one_file(path).map(dedupe_documents)
}

fn collect_files(dir: &Path, out: &mut Vec<std::path::PathBuf>) -> Result<(), String> {
    let entries = fs::read_dir(dir).map_err(|err| format!("read {}: {err}", dir.display()))?;
    for entry in entries {
        let entry = entry.map_err(|err| format!("read {}: {err}", dir.display()))?;
        let path = entry.path();
        if path.is_dir() {
            collect_files(&path, out)?;
        } else if is_corpus_file(&path) {
            out.push(path);
        }
    }
    Ok(())
}

fn is_corpus_file(path: &Path) -> bool {
    matches!(
        path.extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext.to_ascii_lowercase())
            .as_deref(),
        Some("txt" | "md" | "jsonl")
    )
}

fn read_one_file(path: &Path) -> Result<Vec<String>, String> {
    let text = fs::read_to_string(path).map_err(|err| format!("read {}: {err}", path.display()))?;
    let extension = path
        .extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| ext.to_ascii_lowercase())
        .unwrap_or_default();
    if extension == "jsonl" {
        return parse_jsonl(&text);
    }
    let trimmed = text.trim();
    if trimmed.is_empty() {
        Ok(Vec::new())
    } else {
        Ok(vec![trimmed.to_string()])
    }
}

fn parse_jsonl(text: &str) -> Result<Vec<String>, String> {
    let mut documents = Vec::new();
    for (index, line) in text.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if trimmed.starts_with('{') {
            let value: serde_json::Value = serde_json::from_str(trimmed)
                .map_err(|err| format!("jsonl line {}: {err}", index + 1))?;
            let document = value
                .get("text")
                .and_then(|item| item.as_str())
                .or_else(|| value.get("prompt").and_then(|item| item.as_str()))
                .ok_or_else(|| format!("jsonl line {} needs text or prompt", index + 1))?;
            if !document.trim().is_empty() {
                documents.push(document.trim().to_string());
            }
        } else {
            documents.push(trimmed.to_string());
        }
    }
    Ok(documents)
}

fn dedupe_documents(documents: Vec<String>) -> Vec<String> {
    let mut seen = std::collections::BTreeSet::new();
    let mut out = Vec::new();
    for document in documents {
        if seen.insert(text_sha256(&document)) {
            out.push(document);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeSet;

    use serde_json::Value;
    use unicode_normalization::UnicodeNormalization;

    use super::{canonical_fhv1_documents, read_corpus_path, text_sha256};

    fn nfkc_lower(text: &str) -> String {
        text.trim().nfkc().collect::<String>().to_lowercase()
    }

    fn collect_bank_strings(value: &Value, out: &mut Vec<String>) {
        match value {
            Value::String(s) => {
                let trimmed = s.trim();
                if !trimmed.is_empty() {
                    out.push(trimmed.to_string());
                }
            }
            Value::Array(items) => {
                for item in items {
                    collect_bank_strings(item, out);
                }
            }
            Value::Object(map) => {
                if let Some(text) = map.get("text").and_then(Value::as_str) {
                    let trimmed = text.trim();
                    if !trimmed.is_empty() {
                        out.push(trimmed.to_string());
                    }
                    return;
                }
                for item in map.values() {
                    collect_bank_strings(item, out);
                }
            }
            _ => {}
        }
    }

    #[test]
    fn python_and_receta_curated_corpus_meets_diversity_dedup_and_holdout_gates() {
        let suite2: Value = serde_json::from_str(include_str!("suite2_prompts.json"))
            .expect("parse suite2_prompts.json");
        let banks: Value =
            serde_json::from_str(include_str!("../../../tools/fhv1_benchmark_banks.json"))
                .expect("parse fhv1_benchmark_banks.json");

        let mut holdout_raw = BTreeSet::new();
        let mut holdout_folded = BTreeSet::new();
        let mut holdout_strings = Vec::new();
        for key in [
            "clean",
            "clinc_oos",
            "deepset_english",
            "es_injections",
            "es_oos",
        ] {
            if let Some(section) = suite2.get(key) {
                collect_bank_strings(section, &mut holdout_strings);
            }
        }
        collect_bank_strings(&banks, &mut holdout_strings);
        for item in holdout_strings {
            holdout_folded.insert(nfkc_lower(&item));
            holdout_raw.insert(item);
        }

        for (policy_id, expected_first_substr) in [("python", "quicksort"), ("receta", "cebolla")] {
            let docs = canonical_fhv1_documents(policy_id).expect(policy_id);
            assert!(
                (150..=300).contains(&docs.len()),
                "{policy_id} expected 150..=300 docs, got {}",
                docs.len()
            );
            assert!(
                docs[0].contains(expected_first_substr),
                "{policy_id}[0] missing '{expected_first_substr}'"
            );

            let mut seen_sha = BTreeSet::new();
            let mut seen_folded = BTreeSet::new();
            let mut short_count = 0usize;
            let mut medium_count = 0usize;
            let mut multi_para_count = 0usize;
            let mut long_count = 0usize;

            for doc in &docs {
                let trimmed = doc.trim();
                assert!(!trimmed.is_empty(), "{policy_id} has empty doc");
                assert!(
                    seen_sha.insert(text_sha256(trimmed)),
                    "{policy_id} duplicate sha256 for {trimmed}"
                );
                let folded = nfkc_lower(trimmed);
                assert!(
                    seen_folded.insert(folded.clone()),
                    "{policy_id} duplicate nfkc_lower for {trimmed}"
                );
                assert!(
                    !holdout_raw.contains(trimmed) && !holdout_folded.contains(&folded),
                    "{policy_id} overlaps holdout bank: {trimmed}"
                );
                let words = trimmed.split_whitespace().count();
                if words <= 15 {
                    short_count += 1;
                } else if words <= 65 {
                    medium_count += 1;
                } else {
                    long_count += 1;
                }
                if trimmed.contains("\n\n") {
                    multi_para_count += 1;
                }
            }

            assert!(
                short_count >= 20,
                "{policy_id} needs >=20 short docs, got {short_count}"
            );
            assert!(
                medium_count >= 60,
                "{policy_id} needs >=60 medium docs, got {medium_count}"
            );
            assert!(
                long_count >= 20,
                "{policy_id} needs >=20 long docs, got {long_count}"
            );
            assert!(
                multi_para_count >= 20,
                "{policy_id} needs >=20 multi-paragraph docs, got {multi_para_count}"
            );
        }

        let legal = canonical_fhv1_documents("legal").expect("legal fallback");
        assert_eq!(legal.len(), 16);
        assert!(canonical_fhv1_documents("missing").is_err());
    }

    #[test]
    fn ingestion_reads_txt_md_jsonl_and_sorted_directories() {
        let root = std::env::temp_dir().join(format!(
            "fhv1-corpus-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("clock")
                .as_nanos()
        ));
        let nested = root.join("nested");
        std::fs::create_dir_all(&nested).expect("dir");
        std::fs::write(root.join("b.md"), "# Title\n\nBody of the note.\n").expect("md");
        std::fs::write(root.join("a.txt"), "plain document\n").expect("txt");
        std::fs::write(
            nested.join("c.jsonl"),
            "raw line\n{\"text\": \"json text\"}\n{\"prompt\": \"json prompt\"}\n\n",
        )
        .expect("jsonl");
        std::fs::write(root.join("skip.bin"), "ignored").expect("bin");
        let documents = read_corpus_path(&root).expect("read");
        assert_eq!(
            documents,
            vec![
                "plain document".to_string(),
                "# Title\n\nBody of the note.".to_string(),
                "raw line".to_string(),
                "json text".to_string(),
                "json prompt".to_string(),
            ]
        );
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn jsonl_prompts_skip_blank_lines_fail_closed_and_dedupe_across_files() {
        let root = std::env::temp_dir().join(format!(
            "fhv1-corpus-jsonl-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .expect("clock")
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).expect("dir");
        std::fs::write(
            root.join("prompts.jsonl"),
            "{\"prompt\": \"alpha prompt\"}\n\n{\"prompt\": \"beta prompt\"}\n",
        )
        .expect("jsonl");
        let documents = read_corpus_path(&root.join("prompts.jsonl")).expect("prompts");
        assert_eq!(
            documents,
            vec!["alpha prompt".to_string(), "beta prompt".to_string()]
        );

        std::fs::write(
            root.join("broken.jsonl"),
            "{\"prompt\": \"kept\"}\n\n{not-json}\n",
        )
        .expect("broken");
        let err = read_corpus_path(&root.join("broken.jsonl")).expect_err("malformed");
        assert!(err.contains("jsonl line 3"), "{err}");

        std::fs::write(root.join("a.jsonl"), "{\"prompt\": \"shared surface\"}\n").expect("a");
        std::fs::write(root.join("b.txt"), "shared surface\n").expect("b");
        std::fs::write(root.join("c.txt"), "unique surface\n").expect("c");
        let _ = std::fs::remove_file(root.join("prompts.jsonl"));
        let _ = std::fs::remove_file(root.join("broken.jsonl"));
        let deduped = read_corpus_path(&root).expect("dir");
        assert_eq!(
            deduped,
            vec!["shared surface".to_string(), "unique surface".to_string()]
        );
        let _ = std::fs::remove_dir_all(&root);
    }
}
