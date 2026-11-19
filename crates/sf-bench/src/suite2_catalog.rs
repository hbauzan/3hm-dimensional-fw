//! Prompt catalog for Suite 2.
//!
//! English attacks are CLINC OOS lines and English deepset injections.
//! They attach only to domains whose seed sentences are English.
//! Spanish seed domains keep Spanish clean queries and Spanish attacks.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;

use serde::Deserialize;

use crate::canonical_corpus::canonical_seed_corpus;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Suite2Kind {
    Clean,
    Attack,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Suite2Prompt {
    pub domain: &'static str,
    pub kind: Suite2Kind,
    pub attack_type: Option<&'static str>,
    pub text: String,
}

#[derive(Debug, Deserialize)]
struct CatalogFile {
    clean: BTreeMap<String, Vec<String>>,
    en_piggy_hosts: Vec<String>,
    clinc_oos: Vec<String>,
    deepset_english: Vec<String>,
    es_injections: Vec<String>,
    es_piggy_hosts: BTreeMap<String, Vec<String>>,
    es_oos: BTreeMap<String, Vec<String>>,
}

fn catalog() -> &'static CatalogFile {
    static CATALOG: OnceLock<CatalogFile> = OnceLock::new();
    CATALOG.get_or_init(|| {
        serde_json::from_str(include_str!("suite2_prompts.json")).expect("suite 2 prompt catalog")
    })
}

pub fn suite2_matrix_label(domain: &str) -> &'static str {
    let entry = canonical_seed_corpus()
        .iter()
        .find(|item| item.domain_id == domain)
        .unwrap_or_else(|| panic!("unknown canonical domain: {domain}"));
    if entry
        .sentences
        .iter()
        .any(|sentence| has_spanish_mark(sentence))
    {
        "ES"
    } else {
        "EN"
    }
}

fn has_spanish_mark(text: &str) -> bool {
    text.chars().any(|ch| {
        matches!(
            ch,
            'á' | 'é'
                | 'í'
                | 'ó'
                | 'ú'
                | 'ü'
                | 'ñ'
                | 'Á'
                | 'É'
                | 'Í'
                | 'Ó'
                | 'Ú'
                | 'Ü'
                | 'Ñ'
                | '¿'
                | '¡'
        )
    })
}

pub fn suite2_prompts() -> Vec<Suite2Prompt> {
    let file = catalog();
    let mut known = BTreeSet::new();
    for domain in sf_storage::CANONICAL_DOMAINS {
        known.insert(domain);
        let clean = file
            .clean
            .get(domain)
            .unwrap_or_else(|| panic!("missing clean prompts for {domain}"));
        if clean.is_empty() {
            panic!("empty clean prompts for {domain}");
        }
    }
    for key in file
        .clean
        .keys()
        .chain(file.es_oos.keys())
        .chain(file.es_piggy_hosts.keys())
    {
        if !known.contains(key.as_str()) {
            panic!("unknown domain in suite 2 catalog: {key}");
        }
    }
    if file.clinc_oos.is_empty()
        || file.deepset_english.is_empty()
        || file.en_piggy_hosts.is_empty()
    {
        panic!("English attack catalog is empty");
    }
    if file.es_injections.is_empty() {
        panic!("Spanish injection catalog is empty");
    }

    let mut prompts = Vec::new();
    for domain in sf_storage::CANONICAL_DOMAINS {
        let clean = &file.clean[domain];
        for text in clean {
            prompts.push(Suite2Prompt {
                domain,
                kind: Suite2Kind::Clean,
                attack_type: None,
                text: text.clone(),
            });
        }
        if suite2_matrix_label(domain) == "EN" {
            for text in &file.clinc_oos {
                prompts.push(Suite2Prompt {
                    domain,
                    kind: Suite2Kind::Attack,
                    attack_type: Some("clinc_oos"),
                    text: text.clone(),
                });
            }
            for (index, injection) in file.deepset_english.iter().enumerate() {
                let host = &file.en_piggy_hosts[index % file.en_piggy_hosts.len()];
                prompts.push(Suite2Prompt {
                    domain,
                    kind: Suite2Kind::Attack,
                    attack_type: Some("deepset_piggyback"),
                    text: format!("{host}. {injection}"),
                });
            }
        } else {
            let oos = file
                .es_oos
                .get(domain)
                .unwrap_or_else(|| panic!("missing Spanish OOS prompts for {domain}"));
            let hosts = file
                .es_piggy_hosts
                .get(domain)
                .unwrap_or_else(|| panic!("missing Spanish piggyback hosts for {domain}"));
            if oos.is_empty() || hosts.is_empty() {
                panic!("empty Spanish attacks for {domain}");
            }
            for text in oos {
                prompts.push(Suite2Prompt {
                    domain,
                    kind: Suite2Kind::Attack,
                    attack_type: Some("es_oos"),
                    text: text.clone(),
                });
            }
            for (index, host) in hosts.iter().enumerate() {
                let injection = &file.es_injections[index % file.es_injections.len()];
                prompts.push(Suite2Prompt {
                    domain,
                    kind: Suite2Kind::Attack,
                    attack_type: Some("es_piggyback"),
                    text: format!("{host}. {injection}"),
                });
            }
        }
    }

    for prompt in &prompts {
        if prompt.text.to_lowercase().contains("y de paso") {
            panic!(
                "mixed-language connector in suite 2 prompt: {}",
                prompt.text
            );
        }
        if suite2_matrix_label(prompt.domain) == "EN" && has_spanish_mark(&prompt.text) {
            panic!("Spanish mark in English suite 2 prompt: {}", prompt.text);
        }
    }
    prompts
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_keeps_attack_language_with_the_seed_language() {
        let prompts = suite2_prompts();
        assert!(prompts
            .iter()
            .all(|prompt| !prompt.text.to_lowercase().contains("y de paso")));
        assert!(prompts
            .iter()
            .filter(|prompt| suite2_matrix_label(prompt.domain) == "EN")
            .all(|prompt| prompt.domain == "python"));
        assert!(prompts
            .iter()
            .filter(|prompt| suite2_matrix_label(prompt.domain) == "ES")
            .all(|prompt| prompt.domain != "python"));
        assert!(prompts
            .iter()
            .filter(|prompt| prompt.attack_type == Some("clinc_oos"))
            .all(|prompt| suite2_matrix_label(prompt.domain) == "EN"));
        assert!(prompts
            .iter()
            .filter(|prompt| prompt.attack_type == Some("deepset_piggyback"))
            .all(|prompt| suite2_matrix_label(prompt.domain) == "EN"));
        assert!(prompts
            .iter()
            .filter(|prompt| {
                prompt.attack_type == Some("es_oos") || prompt.attack_type == Some("es_piggyback")
            })
            .all(|prompt| suite2_matrix_label(prompt.domain) == "ES"));
        assert!(prompts
            .iter()
            .any(|prompt| prompt.kind == Suite2Kind::Clean && prompt.domain == "python"));
        assert!(prompts
            .iter()
            .any(|prompt| prompt.kind == Suite2Kind::Clean && prompt.domain == "receta"));
    }
}
