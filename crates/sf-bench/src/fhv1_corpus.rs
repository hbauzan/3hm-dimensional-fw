//! Canonical `fhv1` seed documents and file ingestion.

use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use crate::canonical_corpus::canonical_seed_corpus;

const PYTHON_PARAGRAPHS: &str = "\
A Python service keeps its event loop free by awaiting each socket read before it parses the next frame.\n\
\n\
The second paragraph records how a frozen dataclass stores the threshold, the domain name, and the digest without a mutable dictionary.";

const RECETA_PARAGRAPHS: &str = "\
Sofreír la cebolla despacio y sumar el arroz tostado antes de mojar con el primer cucharón de caldo caliente.\n\
\n\
El segundo párrafo deja reposar el guiso tapado para que el almidón espese el fondo sin revolver de más.";

/// SHA-256 of one document. Used to drop duplicate ingested texts.
pub fn text_sha256(text: &str) -> [u8; 32] {
    let digest = Sha256::digest(text.as_bytes());
    let mut out = [0u8; 32];
    out.copy_from_slice(digest.as_slice());
    out
}

/// The 16 canonical sentences plus one two-paragraph document for `python` and `receta`.
pub fn canonical_fhv1_documents(policy_id: &str) -> Result<Vec<String>, String> {
    let domain = canonical_seed_corpus()
        .iter()
        .find(|item| item.domain_id == policy_id)
        .ok_or_else(|| format!("unknown fhv1 policy '{policy_id}'"))?;
    let mut documents: Vec<String> = domain
        .sentences
        .iter()
        .map(|line| (*line).to_string())
        .collect();
    match policy_id {
        "python" => documents.push(PYTHON_PARAGRAPHS.to_string()),
        "receta" => documents.push(RECETA_PARAGRAPHS.to_string()),
        _ => {}
    }
    Ok(documents)
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
    use super::{canonical_fhv1_documents, read_corpus_path};

    #[test]
    fn python_and_receta_keep_the_sixteen_seeds_and_a_second_paragraph() {
        let python = canonical_fhv1_documents("python").expect("python");
        let receta = canonical_fhv1_documents("receta").expect("receta");
        assert_eq!(python.len(), 17);
        assert_eq!(receta.len(), 17);
        assert!(python[0].contains("quicksort"));
        assert!(receta[0].contains("cebolla"));
        assert!(python.last().expect("doc").contains("\n\n"));
        assert!(receta.last().expect("doc").contains("\n\n"));
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
