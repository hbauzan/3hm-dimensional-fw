//! Pre-segmentation input normalizer for anti-smuggling and homoglyph defense.
//!
//! Provides deterministic, low-allocation normalization before `ClauseSegmenter`:
//! 1. Zero-width & invisible control character stripping (ZWSP, ZWNJ, ZWJ, Word Joiner, BOM, Soft Hyphen).
//! 2. Canonical mapping of Cyrillic and Greek homoglyphs to ASCII/Latin.
//! 3. Unicode NFKC normalization.
//! 4. Contiguous Base64 / URL-safe payload inspection and extraction of valid cleartext UTF-8 clauses.

use base64::engine::general_purpose::{STANDARD, URL_SAFE};
use base64::Engine;
use unicode_normalization::UnicodeNormalization;

use crate::segmenter::segment_prompt_clauses;

/// Checks if a character is an invisible evasion control character.
#[inline]
pub fn is_invisible_control(c: char) -> bool {
    matches!(
        c,
        '\u{200B}' // Zero Width Space (ZWSP)
        | '\u{200C}' // Zero Width Non-Joiner (ZWNJ)
        | '\u{200D}' // Zero Width Joiner (ZWJ)
        | '\u{2060}' // Word Joiner
        | '\u{FEFF}' // Zero Width No-Break Space / Byte Order Mark (BOM)
        | '\u{00AD}' // Soft Hyphen
    )
}

/// Maps common Cyrillic and Greek homoglyphs to their visually identical Latin/ASCII counterparts.
#[inline]
pub fn map_homoglyph(c: char) -> char {
    match c {
        // Cyrillic Lowercase
        '\u{0430}' => 'a', // Cyrillic Small Letter A
        '\u{0441}' => 'c', // Cyrillic Small Letter Es
        '\u{0435}' => 'e', // Cyrillic Small Letter Ie
        '\u{0456}' => 'i', // Cyrillic Small Letter Byelorussian-Ukrainian I
        '\u{0458}' => 'j', // Cyrillic Small Letter Je
        '\u{043E}' => 'o', // Cyrillic Small Letter O
        '\u{0440}' => 'p', // Cyrillic Small Letter Er
        '\u{0455}' => 's', // Cyrillic Small Letter Dze
        '\u{0443}' => 'y', // Cyrillic Small Letter U
        '\u{0445}' => 'x', // Cyrillic Small Letter Ha

        // Cyrillic Uppercase
        '\u{0410}' => 'A', // Cyrillic Capital Letter A
        '\u{0412}' => 'B', // Cyrillic Capital Letter Ve
        '\u{0421}' => 'C', // Cyrillic Capital Letter Es
        '\u{0415}' => 'E', // Cyrillic Capital Letter Ie
        '\u{041D}' => 'H', // Cyrillic Capital Letter En
        '\u{0406}' => 'I', // Cyrillic Capital Letter Byelorussian-Ukrainian I
        '\u{0408}' => 'J', // Cyrillic Capital Letter Je
        '\u{041A}' => 'K', // Cyrillic Capital Letter Ka
        '\u{041C}' => 'M', // Cyrillic Capital Letter Em
        '\u{041E}' => 'O', // Cyrillic Capital Letter O
        '\u{0420}' => 'P', // Cyrillic Capital Letter Er
        '\u{0405}' => 'S', // Cyrillic Capital Letter Dze
        '\u{0422}' => 'T', // Cyrillic Capital Letter Te
        '\u{0425}' => 'X', // Cyrillic Capital Letter Ha

        // Greek Lowercase
        '\u{03BF}' => 'o', // Greek Small Letter Omicron
        '\u{03BD}' => 'v', // Greek Small Letter Nu
        '\u{03BA}' => 'k', // Greek Small Letter Kappa
        '\u{03C1}' => 'p', // Greek Small Letter Rho

        // Greek Uppercase
        '\u{0391}' => 'A', // Greek Capital Letter Alpha
        '\u{0392}' => 'B', // Greek Capital Letter Beta
        '\u{0395}' => 'E', // Greek Capital Letter Epsilon
        '\u{0396}' => 'Z', // Greek Capital Letter Zeta
        '\u{0397}' => 'H', // Greek Capital Letter Eta
        '\u{0399}' => 'I', // Greek Capital Letter Iota
        '\u{039A}' => 'K', // Greek Capital Letter Kappa
        '\u{039C}' => 'M', // Greek Capital Letter Mu
        '\u{039D}' => 'N', // Greek Capital Letter Nu
        '\u{039F}' => 'O', // Greek Capital Letter Omicron
        '\u{03A1}' => 'P', // Greek Capital Letter Rho
        '\u{03A4}' => 'T', // Greek Capital Letter Tau
        '\u{03A5}' => 'Y', // Greek Capital Letter Upsilon
        '\u{03A7}' => 'X', // Greek Capital Letter Chi

        other => other,
    }
}

/// Normalized prompt container holding canonical text and decoded payload strings.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormalizedInput {
    /// Canonical NFKC text with homoglyphs mapped and invisible characters stripped.
    pub text: String,
    /// Decoded UTF-8 cleartext strings extracted from high-entropy Base64 payloads.
    pub decoded_payloads: Vec<String>,
}

impl NormalizedInput {
    /// Segments both the primary prompt and all decoded Base64 payloads into clauses.
    pub fn segment_all_clauses(&self) -> Vec<&str> {
        let mut clauses = segment_prompt_clauses(&self.text);
        for payload in &self.decoded_payloads {
            let sub = segment_prompt_clauses(payload);
            clauses.extend(sub);
        }
        clauses
    }
}

/// Deterministic pre-segmentation normalizer.
pub struct InputNormalizer;

impl InputNormalizer {
    /// Normalize an incoming raw prompt string:
    /// 1. Strip invisible control characters.
    /// 2. Map Cyrillic/Greek homoglyphs to ASCII.
    /// 3. Apply Unicode NFKC canonical decomposition & composition.
    /// 4. Inspect high-entropy Base64 payloads (length >= 24) and extract valid cleartext UTF-8 clauses.
    pub fn normalize(input: &str) -> NormalizedInput {
        // Step 1 & 2: Homoglyph mapping and invisible stripping before/during NFKC
        let homoglyph_cleaned: String = input
            .chars()
            .filter(|&c| !is_invisible_control(c))
            .map(map_homoglyph)
            .collect();

        // Step 3: NFKC normalization
        let nfkc_text: String = homoglyph_cleaned
            .nfkc()
            .filter(|&c| !is_invisible_control(c))
            .collect();

        // Step 4: Base64 payload inspection
        let decoded_payloads = Self::extract_base64_payloads(&nfkc_text);

        NormalizedInput {
            text: nfkc_text,
            decoded_payloads,
        }
    }

    /// Detects contiguous Base64 candidate tokens (len >= 24) and decodes valid UTF-8 cleartext.
    fn extract_base64_payloads(text: &str) -> Vec<String> {
        let mut payloads = Vec::new();

        // Split text into whitespace and punctuation delimited candidate slices
        let mut start: Option<usize> = None;
        let bytes = text.as_bytes();

        for (i, &b) in bytes.iter().enumerate() {
            let is_b64_char = b.is_ascii_alphanumeric()
                || b == b'+'
                || b == b'/'
                || b == b'='
                || b == b'-'
                || b == b'_';

            if is_b64_char {
                if start.is_none() {
                    start = Some(i);
                }
            } else if let Some(s) = start.take() {
                let candidate = &text[s..i];
                if candidate.len() >= 24 {
                    if let Some(decoded) = Self::try_decode_payload(candidate) {
                        payloads.push(decoded);
                    }
                }
            }
        }

        if let Some(s) = start {
            let candidate = &text[s..];
            if candidate.len() >= 24 {
                if let Some(decoded) = Self::try_decode_payload(candidate) {
                    payloads.push(decoded);
                }
            }
        }

        payloads
    }

    /// Attempts to decode a Base64 candidate string and validates that it contains printable UTF-8 text.
    fn try_decode_payload(candidate: &str) -> Option<String> {
        // Trim standard padding to avoid false failures
        let trimmed = candidate.trim_end_matches('=');
        if trimmed.len() < 24 {
            return None;
        }

        // Measure Shannon entropy to filter out low-entropy runs (e.g. "AAAAAAAAAAAAAAAAAAAAAAAA")
        if shannon_entropy(candidate) < 2.2 {
            return None;
        }

        // Try standard base64 decoding
        let decoded_bytes = STANDARD
            .decode(candidate)
            .or_else(|_| URL_SAFE.decode(candidate))
            .or_else(|_| {
                // Try padding if missing
                let padded = match candidate.len() % 4 {
                    2 => format!("{candidate}=="),
                    3 => format!("{candidate}="),
                    _ => candidate.to_string(),
                };
                STANDARD
                    .decode(&padded)
                    .or_else(|_| URL_SAFE.decode(&padded))
            })
            .ok()?;

        let cleartext = String::from_utf8(decoded_bytes).ok()?;
        let trimmed_cleartext = cleartext.trim();

        // Must contain alphabetic characters and not be filled with binary control codes
        if trimmed_cleartext.len() < 3 {
            return None;
        }

        let has_alpha = trimmed_cleartext.chars().any(|c| c.is_alphabetic());
        let all_printable = trimmed_cleartext
            .chars()
            .all(|c| !c.is_control() || c == '\n' || c == '\r' || c == '\t');

        if has_alpha && all_printable {
            Some(trimmed_cleartext.to_string())
        } else {
            None
        }
    }
}

/// Compute Shannon entropy in bits per character.
fn shannon_entropy(s: &str) -> f64 {
    let mut counts = [0usize; 256];
    let mut total = 0usize;

    for &b in s.as_bytes() {
        counts[b as usize] += 1;
        total += 1;
    }

    if total == 0 {
        return 0.0;
    }

    let mut entropy = 0.0f64;
    let total_f = total as f64;

    for &count in &counts {
        if count > 0 {
            let p = count as f64 / total_f;
            entropy -= p * p.log2();
        }
    }

    entropy
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_zero_width_control_stripping() {
        // "receta" with injected invisible control characters
        let raw = "r\u{200B}e\u{200C}c\u{200D}e\u{2060}t\u{FEFF}\u{00AD}a";
        let norm = InputNormalizer::normalize(raw);
        assert_eq!(norm.text, "receta");
        assert!(norm.decoded_payloads.is_empty());
    }

    #[test]
    fn test_cyrillic_and_greek_homoglyphs_to_ascii() {
        // "pуthоn" using Cyrillic у (0443) and Cyrillic о (043e)
        let cyrillic_python = "p\u{0443}th\u{043E}n";
        let norm = InputNormalizer::normalize(cyrillic_python);
        assert_eq!(norm.text, "python");

        // "rесеtа" using Cyrillic е (0435), с (0441), е (0435), а (0430)
        let cyrillic_receta = "r\u{0435}\u{0441}\u{0435}t\u{0430}";
        let norm_receta = InputNormalizer::normalize(cyrillic_receta);
        assert_eq!(norm_receta.text, "receta");

        // Greek omicron and nu
        let greek = "\u{03BF}\u{03BD}"; // ον
        let norm_greek = InputNormalizer::normalize(greek);
        assert_eq!(norm_greek.text, "ov");
    }

    #[test]
    fn test_nfkc_fullwidth_normalization() {
        // Fullwidth Latin: "ｐｙｔｈｏｎ" (U+FF50 U+FF59 U+FF54 U+FF48 U+FF4F U+FF4E)
        let fullwidth = "ｐｙｔｈｏｎ";
        let norm = InputNormalizer::normalize(fullwidth);
        assert_eq!(norm.text, "python");
    }

    #[test]
    fn test_base64_payload_detection_and_extraction() {
        // Base64 encoding of "receta de risotto con queso y hongos"
        // Length of base64 token is 48 chars (>= 24)
        let b64 = "cmVjZXRhIGRlIHJpc290dG8gY29uIHF1ZXNvIHkgaG9uZ29z";
        let prompt = format!("Please review this encoded string: {b64} for performance.");
        let norm = InputNormalizer::normalize(&prompt);

        assert_eq!(norm.decoded_payloads.len(), 1);
        assert_eq!(
            norm.decoded_payloads[0],
            "receta de risotto con queso y hongos"
        );

        let clauses = norm.segment_all_clauses();
        assert!(clauses.iter().any(|c| c.contains("receta de risotto")));
    }

    #[test]
    fn test_low_entropy_base64_false_positive_prevention() {
        let repeated = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
        let norm = InputNormalizer::normalize(repeated);
        assert!(norm.decoded_payloads.is_empty());
    }
}
